import json
import logging
import os
import pathlib
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from enum import Enum
from typing import Any

from wcferry import WxMsg

TEMP_DIR = 'files-save'
LOG = logging.getLogger("wcf_utils")


def timestamp() -> str:
    """ 时间戳字符串: YYmmdd_HHMMDD"""
    return str(datetime.now().strftime("%Y%m%d_%H%M%S"))


def temp_file(name: str) -> str:
    """ 返回临时文件名 """
    return str((get_path(TEMP_DIR) / name).resolve())


def get_path(folder: str) -> pathlib.Path:
    """ 返回文件夹 Path对象. 若不存在, 创建文件夹。"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = pathlib.Path(sys._MEIPASS).parent  # pylint: disable=W0212,E1101
    except Exception:  # pylint: disable=broad-except
        base_path = pathlib.Path('.')

    full_path = base_path / folder
    if not full_path.exists():
        full_path.mkdir(parents=True, exist_ok=True)
    return full_path


def temp_dir() -> str:
    """ 返回临时文件夹 """
    return str(get_path(TEMP_DIR).resolve())


class ContentType(Enum):
    """ 表示用微信发送的消息的类型"""
    text = 1  # 文字
    image = 3  # 图片
    link = 4  # 链接
    file = 6  # 文件
    voice = 34  # 语音
    video = 43  # 视频
    ERROR = 9000  # 错误
    UNSUPPORTED = 9001  # 不支持类型


class ChatMsg:
    """ 代表某种类型的消息, 用于内部数据传递 """

    def __init__(self, type: ContentType, content: str) -> None:
        """ 初始化
        Args:
            type (ContentType): 附件类型
            content (str): 附件内容
        """
        self.type = type
        self.content = content

    def to_dict(self) -> dict[str, Any]:
        """ 将对象转换为可序列化的字典 """
        return {
            'type': self.type.value,
            'content': self.content
        }

    def __str__(self) -> str:
        """ 返回对象的字符串表示形式 """
        return f"ChatMsg(type={self.type.value}, content={self.content})"


class WcfUtils:
    _instance = None
    wcf = None

    def __new__(cls, wcf=None):
        if cls._instance is None:
            cls._instance = super(WcfUtils, cls).__new__(cls)
            cls._instance.__init_once(wcf)
        return cls._instance

    def __init_once(self, wcf):
        if not hasattr(self, 'initialized'):  # 防止重复初始化
            self.wcf = wcf
            self.initialized = True

    def get_video(self, msgid: str, extra: str) -> str:
        """ 下载消息附件（视频、文件）
        Args:
            msgid (str): 消息id
            extra (str): 正常消息的extra

        Returns:
            str: 下载的文件路径, 若失败返回None
        """
        filename = self.get_msg_extra(msgid, extra)
        if filename:  # 原来下载过
            if os.path.exists(filename):  # 文件还存在
                return filename
            else:
                pass
        else:
            filename = temp_file(f"Wechat_video_{timestamp()}.mp4")

        # 需要重新下载
        res = self.wcf.download_attach(msgid, filename, "")
        if res == 0:
            return filename
        else:
            return None

    def get_msg_text(self, msg: WxMsg) -> str:
        """ 返回消息的文字部分, 没有则返回空字符串"""
        if msg.type == 1:
            return msg.content
        if msg.type == 34:
            audio_file = self.wcf.get_audio_msg(msg.id, temp_dir())
            return audio_file
        if msg.type == 49:  # 引用
            content = ET.fromstring(msg.content)
            title = content.find('appmsg/title')
            return title.text if title is not None else ""
        return ""

    def get_refer_content(self, msg: WxMsg) -> ChatMsg:
        """返回被引用的内容, 如果没有返回None
        Args:
            msg (WxMsg): 微信消息对象

        Returns:
            (WxMsgType, str): 类型, 内容(文本或路径)
        """
        # 找到引用的消息
        if msg.type != 49:  # 非49 不是引用
            return None

        try:
            content = ET.fromstring(msg.content)
            refermsg_xml = content.find('appmsg/refermsg')
            if refermsg_xml is None:
                return None

            # 判断refermsg类型
            refer_type = int(refermsg_xml.find('type').text)  # 被引用消息type
            refer_id = int(refermsg_xml.find('svrid').text)

            if refer_type == 1:  # 文本
                return ChatMsg(ContentType.text, refermsg_xml.find('content').text)

            elif refer_type == 3:  # 图片 下载图片
                refer_extra = self.get_msg_extra(refer_id, msg.extra)
                if refer_extra:
                    dl_file = self.get_image(refer_id, refer_extra)
                    if dl_file:
                        return ChatMsg(ContentType.image, dl_file)
                    else:
                        LOG.warning("无法获取dl_file, 消息id=%s", str(refer_id))
                else:
                    LOG.warning("无法获取refer_extra, 消息id=%s", str(refer_id))
                LOG.warning("无法获取引用图片, 消息id=%s", str(refer_id))
                return ChatMsg(ContentType.ERROR, None)

            elif refer_type == 34:  # 语音: 下载语音文件
                audio_file = self.wcf.get_audio_msg(refer_id, temp_dir())
                if audio_file:
                    return ChatMsg(ContentType.voice, audio_file)
                else:
                    LOG.warning("无法获取引用语音, 消息ID=%s", str(refer_id))
                    return ChatMsg(ContentType.ERROR, None)

            elif refer_type == 43:  # 视频: 下载视频
                video_file = self.get_video(refer_id, msg.extra)
                if video_file:
                    return ChatMsg(ContentType.video, video_file)
                else:
                    LOG.warning("无法获取引用的视频, 引用消息id=%s", str(refer_id))
                    return ChatMsg(ContentType.ERROR, None)

            elif refer_type == 49:  # 文件，链接，公众号文章，或另一个引用. 需要进一步判断
                refer_content_xml = ET.fromstring(refermsg_xml.find('content').text)
                content_type = int(refer_content_xml.find('appmsg/type').text)
                if content_type in [4, 5]:  # 链接或公众号文章
                    texts = {}
                    title = refer_content_xml.find('appmsg/title')
                    if title is not None:
                        texts['title'] = title.text
                    des = refer_content_xml.find('appmsg/des')
                    if des is not None:
                        texts['des'] = des.text
                    url = refer_content_xml.find('appmsg/url')
                    if url is not None:
                        texts['url'] = url.text
                    text = json.dumps(texts)
                    return ChatMsg(ContentType.link, text)

                elif content_type == 6:  # 文件
                    # refer_msg = self.msg_dict.get(refer_id, None)
                    refer_extra = self.get_msg_extra(refer_id, msg.extra)
                    if refer_extra:
                        dl_file = refer_extra
                        # self.wcf.download_attach() 会崩溃
                        if os.path.exists(dl_file):
                            return ChatMsg(ContentType.file, dl_file)

                    LOG.warning("无法获得被引用消息中的文件, 消息id=%s", str(refer_id))
                    return ChatMsg(ContentType.ERROR, None)

                elif content_type == 57:  # 另一引用 输出文本部分
                    refer_title = refer_content_xml.find('appmsg/title').text
                    return ChatMsg(ContentType.text, refer_title)

                else:
                    LOG.warning("不支持该类型引用, type=%s, content_type=%s", str(refer_type),
                                str(content_type))
                    return ChatMsg(ContentType.UNSUPPORTED, None)
            else:  # 其他引用 TBA 视频，文章等
                LOG.warning("不支持该类型引用, type=%s", str(refer_type))
                return ChatMsg(ContentType.UNSUPPORTED, None)

        except Exception as e:
            LOG.error("读取引用消息发生错误: %s", e)
            return ChatMsg(ContentType.ERROR, None)

    def get_msg_from_db(self, msgid: str) -> dict:
        """ 从数据库查找 msgid 的信息,返回dict. 找不到则返回 None"""
        dbs = self.wcf.get_dbs()
        # find all strings from dbs like "MSG#.db" where # is a single digit number
        msg_dbs = [db for db in dbs if re.match(r"MSG\d\.db", db)]
        query = f"SELECT * FROM MSG WHERE MsgSvrID={msgid}"
        for db in msg_dbs:
            msg_data = self.wcf.query_sql(db, query)
            if msg_data:
                return msg_data[0]
        return None

    def get_msg_extra(self, msgid: str, sample_extra: str) -> str:
        """ 获取历史消息的extra

        Args:
            msgid (str): WxMsg的id
            sample_extra (str): 同个微信号正常消息的extra
        Returns:
            str: 消息extra, 若无法获取返回None
        """

        msg_data = self.get_msg_from_db(msgid)
        if not msg_data:
            return None
        bextra = msg_data.get('BytesExtra')

        # 多种pattern搜索
        patterns = [
            b'\x08\x04\x12.(.*?)\x1a',  # 图片
            b'\x08\x04\x12.(.*?)$',  # 文件
            b'\x08\x04\x12.(.*?)\x1a'  # 自己发的文件
        ]
        match = None
        for p in patterns:
            match = re.compile(p).search(bextra)
            if match:
                break
        if not match:
            return None

        extra = match.group(1)
        new_extra: str = extra.decode('utf-8')
        # 拼接new_extra和sample_extra获得文件路径
        keyword = "FileStorage"
        # 获取sample_extra keyword之前的部分
        part1 = sample_extra.split(keyword)[0]
        # 获取new_extra中，第一个keyword之后的部分
        key_index = new_extra.find(keyword)
        if key_index == -1:  # 没找到
            part2 = new_extra
        else:
            part2 = new_extra[key_index:]

        # 拼接 part1 part2 得到完整path
        full_path = (pathlib.Path(part1) / pathlib.Path(part2)).resolve().as_posix()
        return full_path

    def get_image(self, msgid: str, extra: str) -> str:
        """ 下载图片。若已经下载，直接返回已经存在的文件。

        Args:
            msgid (str): 消息id
            extra (str): 消息extra

        Returns:
            str: 下载的文件路径。若失败返回None
        """

        # 获得文件主名
        pattern = r'/([^/]+)\.[^\.]+$'
        match = re.search(pattern, extra)
        if not match:
            return None
        main_name = match.group(1)

        # 判断文件是否已经下载。如果已经下载，直接返回存在的文件
        dl_file = self.downloaded_image(main_name)
        if dl_file:
            return dl_file

        # 若不存在，调用wcf下载图片
        dl_file = self.download_with_retries(msgid, extra, temp_dir())
        if dl_file:
            return dl_file
        return None

    def download_with_retries(self, msgid, extra, temp_dir, max_retries=3, delay=2):
        """下载文件并重试指定次数

        Args:
            msgid: 消息ID
            extra: 附加信息
            temp_dir: 临时目录
            max_retries: 最大重试次数
            delay: 重试前的等待时间（秒）

        Returns:
            下载的文件路径或 None 如果下载失败
        """
        attempt = 0
        dl_file = None

        while attempt < max_retries:
            dl_file = self.wcf.download_image(msgid, extra, temp_dir)
            if dl_file:
                return dl_file
            attempt += 1
            LOG.warning(f"下载失败，正在重试 {attempt}/{max_retries}...")
            time.sleep(delay)

        LOG.error("下载失败，所有重试均已失败")
        return None

    @staticmethod
    def downloaded_image(main_name: str) -> str:
        """ 如果图片已经下载，返回路径。否则返回 None"""

        tmp = get_path(TEMP_DIR)
        for file in tmp.iterdir():
            if file.is_file() and file.name.startswith(f"{main_name}."):
                return str(file.resolve())
        return None
