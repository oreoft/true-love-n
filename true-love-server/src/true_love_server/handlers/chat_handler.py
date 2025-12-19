# -*- coding: utf-8 -*-
"""
Chat Handler - 聊天处理器

处理普通聊天消息（兜底处理器）。
"""

import logging
import re
from typing import Optional

from .base_handler import BaseHandler
from .registry import register_handler
from ..models import ChatMsg
from ..services import do_asr, ChatService, ImageService
from ..core import Config

LOG = logging.getLogger("ChatHandler")


@register_handler
class ChatHandler(BaseHandler):
    """
    聊天处理器
    
    作为兜底处理器，处理所有未被其他处理器处理的消息。
    """
    
    name = "ChatHandler"
    priority = 1000  # 最低优先级，作为兜底
    
    def __init__(self):
        self.chat_service = ChatService()
        self.image_service = ImageService()
        config = Config()
        self.chatbot_enabled = config.ENABLE_BOT is not None
    
    def can_handle(self, msg: ChatMsg, cleaned_content: str) -> bool:
        # 作为兜底，始终返回 True
        return True
    
    def handle(self, msg: ChatMsg, cleaned_content: str) -> Optional[str]:
        """处理消息"""
        # 如果没有配置聊天机器人
        if not self.chatbot_enabled:
            return "诶嘿~你叫我有什么事吗？我还在睡觉觉呢~"
        
        context_id = msg.chat_id if msg.from_group() else msg.sender
        
        # 引用消息处理
        if msg.has_refer():
            return self._handle_refer_message(msg, cleaned_content, context_id)
        
        # 普通消息处理
        return self._handle_normal_message(msg, cleaned_content, context_id)
    
    def _handle_normal_message(
        self,
        msg: ChatMsg,
        cleaned_content: str,
        context_id: str
    ) -> Optional[str]:
        """处理普通消息"""
        q = cleaned_content
        
        # 文本消息
        if msg.is_text():
            url = self._extract_first_link(q)
            if url:
                q = f"{q}, quoted content: {self._crawl_content(url)}"
            self.chat_service.get_answer(q, context_id, msg.sender)
            return None
        
        # 链接消息
        if msg.is_link() and msg.url:
            q = f"{q}, quoted content: {self._crawl_content(msg.url)}"
            self.chat_service.get_answer(q, context_id, msg.sender)
            return None
        
        # 图片消息
        if msg.is_image() and msg.file_path:
            self.image_service.handle_image_request(
                '请分析图片或者回答图片内容',
                msg.file_path,
                context_id,
                msg.sender
            )
            return None
        
        # 语音消息
        if msg.is_voice():
            voice_text = msg.voice_text
            if not voice_text and msg.file_path:
                voice_text = do_asr(msg.file_path)
            if voice_text:
                self.chat_service.get_answer(voice_text, context_id, msg.sender)
                return None
        
        # 其他类型
        return "呜呜~这种类型的消息我还看不懂捏，但我会努力学习的啦~"
    
    def _handle_refer_message(
        self,
        msg: ChatMsg,
        cleaned_content: str,
        context_id: str
    ) -> Optional[str]:
        """处理引用消息"""
        refer_type = msg.get_refer_type()
        refer_content = msg.get_refer_content()
        refer_file = msg.get_refer_file_path()
        q = cleaned_content
        
        LOG.info(
            "处理引用消息, type=%s, content=%s",
            refer_type,
            refer_content[:50] if refer_content else None
        )
        
        # 引用图片 -> 图片分析或图生图
        if refer_type == 'image' and refer_file:
            LOG.info("收到引用图片, 判断分析还是生图: %s", q)
            self.image_service.handle_image_request(q, refer_file, context_id, msg.sender)
            return None
        
        # 引用文本或链接
        if refer_type in ['text', 'link'] and refer_content:
            url = self._extract_first_link(refer_content)
            if url:
                refer_text = self._crawl_content(url)
            else:
                refer_text = refer_content
            q = f"{q}, quoted content: {refer_text}"
            LOG.info("收到引用文本: %s", q[:100])
            self.chat_service.get_answer(q, context_id, msg.sender)
            return None
        
        # 引用语音
        if refer_type == 'voice':
            voice_text = msg.refer_msg.voice_text if msg.refer_msg else None
            if not voice_text and refer_file:
                voice_text = do_asr(refer_file)
            if voice_text:
                q = f"{q}, quoted asr content: {voice_text}"
                self.chat_service.get_answer(q, context_id, msg.sender)
                return None
        
        # 引用文件（检查是否是音频文件）
        if refer_type == 'file':
            if refer_file and ('m4a' in refer_file or 'mp3' in refer_file):
                voice_text = do_asr(refer_file)
                if voice_text:
                    q = f"{q}, quoted asr content: {voice_text}"
                    self.chat_service.get_answer(q, context_id, msg.sender)
                    return None
        
        # 其他引用类型
        return "诶嘿~这种引用类型我还看不懂呢，把内容复制出来给我看看吧~"
    
    @staticmethod
    def _extract_first_link(text: str) -> Optional[str]:
        """提取文本中的第一个链接"""
        url_pattern = re.compile(r'https?://[^\s]+')
        match = url_pattern.search(text)
        if match:
            return match.group()
        return None
    
    @staticmethod
    def _crawl_content(url: str) -> str:
        """爬取链接内容"""
        if not url:
            return ""
        try:
            import requests
            request_url = "https://www.textise.net/showtext.aspx?strURL=" + url
            headers = {'Accept': 'application/json', 'User-Agent': 'PostmanRuntime/7.40.0'}
            response = requests.get(url=request_url, headers=headers, timeout=30)
            
            # 兼容处理：先尝试 JSON 解析，失败则使用纯文本
            try:
                response_data = response.json()
                content = response_data.get('data', {}).get('content', '')
            except (ValueError, requests.exceptions.JSONDecodeError):
                # Jina 返回的不是 JSON，直接使用文本内容
                content = response.text
            
            if not content:
                content = response.text
            
            content = re.sub(r'\(http.*?\)', '', content)
            content = content.replace('[]', '').replace('\n\n', '\n').strip()
            return content
        except Exception:
            LOG.exception("crawl_content error, url: %s", url)
            return '内容提供失败(你自己联网分析链接内容！！！)'
