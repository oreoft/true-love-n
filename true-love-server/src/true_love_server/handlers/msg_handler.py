# -*- coding: utf-8 -*-
"""
Message Handler - 消息处理器

处理各种类型的消息，调用对应的服务。
"""

import logging
import re

from ..core import local_msg_id
from ..services import do_asr
from ..models.chat_msg import ChatMsg, MsgType
from .chat_msg_handler import ChatMsgHandler
from .trig_manage_handler import TrigManageHandler
from .trig_remainder_handler import TrigRemainderHandler
from .trig_search_handler import TrigSearchHandler
from .trig_task_handler import TrigTaskHandler

handler = ChatMsgHandler()
LOG = logging.getLogger("MsgHandler")


class MsgHandler:

    def __init__(self):
        self.LOG = logging.getLogger("MsgHandler")

    def handler_msg(self, msg: ChatMsg) -> str:
        """
        处理消息
        
        Args:
            msg: 聊天消息
            
        Returns:
            回复内容
        """
        # 清理消息内容
        q: str = msg.content.replace("@真爱粉", "").replace("zaf", "").strip()
        
        # 设置上下文（用于追踪）
        local_msg_id.set(f"{msg.sender}_{msg.chat_id}")
        
        # ==================== 特殊命令处理 ====================
        
        # 查询任务
        if q.startswith('$查询'):
            self.LOG.info(f"收到: {msg.sender}, 查询任务: {q}")
            return TrigSearchHandler().run(q)

        # 执行任务
        if q.startswith('$执行'):
            self.LOG.info(f"收到: {msg.sender}, 执行任务: {q}")
            return TrigTaskHandler().run(q, msg.sender, msg.chat_id)

        # 提醒任务
        if q.startswith('$提醒'):
            self.LOG.info(f"收到: {msg.sender}, 提醒任务: {q}")
            target = msg.chat_id if msg.from_group() else msg.sender
            return TrigRemainderHandler().router(q, target, msg.sender)

        # 管理任务
        if q.startswith('$管理'):
            self.LOG.info(f"收到: {msg.sender}, 管理任务: {q}")
            return TrigManageHandler().run(q, msg.sender)

        # ==================== AI 聊天处理 ====================
        
        # 如果没有配置聊天机器人
        if not handler.chatbot:
            return "你@我干嘛？"

        # 获取聊天上下文ID
        context_id = msg.chat_id if msg.from_group() else msg.sender

        # ==================== 引用消息处理 ====================
        
        if msg.has_refer():
            return self._handle_refer_message(msg, q, context_id)

        # ==================== 图片生成 ====================
        
        if q.startswith('生成') and ('片' in q or '图' in q):
            self.LOG.info(f"收到: {msg.sender}, 生成图片: {q}")
            return handler.gen_img(q, context_id, msg.sender)

        # ==================== 普通消息处理 ====================
        
        # 文本消息
        if msg.is_text():
            # 检查是否包含链接
            url = self.extract_first_link(q)
            if url:
                q = f"{q}, quoted content: {self.crawl_content(url)}"
            return handler.get_answer(q, context_id, msg.sender)

        # 链接消息
        if msg.is_link() and msg.url:
            q = f"{q}, quoted content: {self.crawl_content(msg.url)}"
            return handler.get_answer(q, context_id, msg.sender)
    
        # 图片消息（私聊直接分析）
        if msg.is_image() and not msg.from_group():
            if msg.file_path:
                return handler.gen_img_by_img('请分析图片或者回答图片内容', msg.file_path, context_id, msg.sender)
            return "图片无法获取，请重试"

        # 语音消息
        if msg.is_voice():
            # 优先使用 base 端转好的文字
            voice_text = msg.voice_text
            if not voice_text and msg.file_path:
                # 降级：自己做 ASR
                voice_text = do_asr(msg.file_path)
            if voice_text:
                return handler.get_answer(voice_text, context_id, msg.sender)
            return "语音无法识别，请重试"

        # 其他类型
        return "啊哦~ 现在这个消息暂时我还看不懂, 但我会持续学习的~"

    def _handle_refer_message(self, msg: ChatMsg, q: str, context_id: str) -> str:
        """处理引用消息"""
        refer_type = msg.get_refer_type()
        refer_content = msg.get_refer_content()
        refer_file = msg.get_refer_file_path()
        
        self.LOG.info(f"处理引用消息, type={refer_type}, content={refer_content[:50] if refer_content else None}")
        
        # 引用图片 -> 图片分析或图生图
        # if refer_type == MsgType.IMAGE:
        #     if refer_file:
        #         self.LOG.info(f"收到引用图片, 判断分析还是生图: {q}")
        #         return handler.gen_img_by_img(q, refer_file, context_id, msg.sender)
        #     return "引用的图片无法获取"

        # 引用文本或链接
        if refer_type in [MsgType.TEXT, MsgType.LINK]:
            if refer_content:
                # 检查是否包含链接
                url = self.extract_first_link(refer_content)
                if url:
                    refer_text = self.crawl_content(url)
                else:
                    refer_text = refer_content
                q = f"{q}, quoted content: {refer_text}"
                self.LOG.info(f"收到引用文本: {q[:100]}")
                return handler.get_answer(q, context_id, msg.sender)
            return "引用的内容无法获取"

        # 引用语音
        if refer_type == MsgType.VOICE:
            voice_text = msg.refer_msg.get("voice_text") if msg.refer_msg else None
            if not voice_text and refer_file:
                voice_text = do_asr(refer_file)
            if voice_text:
                q = f"{q}, quoted asr content: {voice_text}"
                return handler.get_answer(q, context_id, msg.sender)
            return "引用的语音无法识别"

        # 引用文件（检查是否是音频文件）
        if refer_type == MsgType.FILE:
            if refer_file and ('m4a' in refer_file or 'mp3' in refer_file):
                voice_text = do_asr(refer_file)
                if voice_text:
                    q = f"{q}, quoted asr content: {voice_text}"
                    return handler.get_answer(q, context_id, msg.sender)

        # 其他引用类型
        return "啊哦~ 现在这个类型引用我还看不懂, 不如你把内容复制出来给我看看呢"

    @staticmethod
    def extract_first_link(text: str) -> str | None:
        """提取文本中的第一个链接"""
        url_pattern = re.compile(r'https?://[^\s]+')
        match = url_pattern.search(text)
        if match:
            return match.group()
        return None

    @staticmethod
    def crawl_content(url: str) -> str:
        """爬取链接内容"""
        if not url:
            return ""
        try:
            import requests
            request_url = "https://www.textise.net/showtext.aspx?strURL=" + url
            headers = {'Accept': 'application/json', 'User-Agent': 'PostmanRuntime/7.40.0'}
            response = requests.get(url=request_url, headers=headers, timeout=30)
            response_data = response.json()
            content = response_data.get('data', {}).get('content', '')
            # 清理内容
            content = re.sub(r'\(http.*?\)', '', content)
            content = content.replace('[]', '').replace('\n\n', '\n').strip()
            return content
        except Exception:
            LOG.exception(f"crawl_content error, url: {url}")
            return '内容解析失败(请agent自己联网分析内容-这段内容不要告诉给用户！！！)'
