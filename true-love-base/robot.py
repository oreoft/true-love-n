# -*- coding: utf-8 -*-

import logging
from queue import Empty
from threading import Thread

from wcferry import Wcf, WxMsg

import server_client


class Robot:

    def __init__(self, wcf: Wcf) -> None:
        self.wcf = wcf
        self.LOG = logging.getLogger("Robot")
        self.wxid = self.wcf.get_self_wxid()
        self.allContacts = self.get_all_contacts()
        self.LOG.info("真爱粉启动成功···")

    def forward_msg(self, msg: WxMsg) -> str:
        # 这里进行转发消息
        return server_client.get_chat(msg)

    def enable_receiving_msg(self) -> None:
        def inner_process_msg(wcf: Wcf):
            while wcf.is_receiving_msg():
                try:
                    msg = wcf.get_msg()
                    if 'weixin' in msg.sender:
                        continue
                    self.LOG.info("监听到消息:[%s]", msg)
                    # 如果群消息,并且艾特,转发
                    if msg.from_group() and (
                            msg.is_at(wcf.self_wxid) or '@真爱粉' in msg.content or 'zaf' in msg.content):
                        self.send_text_msg(self.forward_msg(msg), msg.roomid, msg.sender)
                    # 如果是群消息 但是没有艾特, 直接过
                    if msg.from_group():
                        continue
                    # 剩下的都是私聊消息, 默认全部转发
                    self.send_text_msg(self.forward_msg(msg), msg.sender)
                except Empty:
                    continue  # Empty message
                except Exception as e:
                    self.LOG.error(f"Receiving message error: {e}")

        self.wcf.enable_receiving_msg()
        Thread(target=inner_process_msg, name="GetMessage", args=(self.wcf,), daemon=True).start()

    def send_img_msg(self, path: str, receiver: str) -> int:
        """发送图片，非线程安全

        Args:
            path (str): 图片路径，如：`C:/project/trueLoveBase/TEQuant.jpeg` 或 `https://raw.githubusercontent.com/lich0821/true-love-n/master/assets/TEQuant.jpg`
            receiver (str): 消息接收人，wxid 或者 roomid

        Returns:
            int: 0 为成功，其他失败
        """
        return self.wcf.send_image(path, receiver)

    def send_text_msg(self, msg: str, receiver: str, at_list: str = "") -> None:
        """ 发送消息
        :param msg: 消息字符串
        :param receiver: 接收人wxid或者群id
        :param at_list: 要@的wxid, @所有人的wxid为：nofity@all
        """

        # 发送内容为空, 直接过滤
        if msg == "":
            return
        # msg 中需要有 @ 名单中一样数量的 @
        ats = ""
        if at_list:
            wxids = at_list.split(",")
            for wxid in wxids:
                # 这里偷个懒，直接 @昵称。有必要的话可以通过 MicroMsg.db 里的 ChatRoom 表，解析群昵称
                ats += f" @{self.allContacts.get(wxid, '')}"

        # {msg}{ats} 表示要发送的消息内容后面紧跟@，例如 北京天气情况为：xxx @张三，微信规定需这样写，否则@不生效
        if ats == "":
            self.LOG.info(f"给:[{receiver}], 发送:[{msg}]")
            self.wcf.send_text(f"{msg}", receiver, at_list)
        else:
            self.LOG.info(f"给:[{receiver}], 发送:[{ats}\r{msg}]")
            self.wcf.send_text(f"{ats}\n\n{msg}", receiver, at_list)

    def get_all_contacts(self) -> dict:
        """
        获取联系人（包括好友、公众号、服务号、群成员……）
        格式: {"wxid": "NickName"}
        """
        contacts = self.wcf.query_sql("MicroMsg.db", "SELECT UserName, NickName FROM Contact;")
        return {contact["UserName"]: contact["NickName"] for contact in contacts}

    def get_contacts_by_room_id(self, room_id) -> dict:
        """获取群成员
         Args:
           roomid (str): 群的 id
        Returns:
           Dict: 群成员列表: {wxid1: 昵称1, wxid2: 昵称2, ...}
         """
        return self.wcf.get_chatroom_members(room_id)
