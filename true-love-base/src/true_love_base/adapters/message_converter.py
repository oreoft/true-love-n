# -*- coding: utf-8 -*-
"""
Message Converter - wxautox4 消息转换器

将 wxautox4 的消息对象转换为统一的 BaseMessage 模型。
"""

import logging
from typing import Any, Optional

from true_love_base.core.media_handler import MediaHandler
from true_love_base.models.message import (
    BaseMessage,
    TextMessage,
    ImageMessage,
    VoiceMessage,
    VideoMessage,
    FileMessage,
    UnknownMessage,
)

LOG = logging.getLogger("MessageConverter")


class WxAutoMessageConverter:
    """
    wxautox4 消息转换器
    
    将 wxautox4 的消息对象转换为统一的 BaseMessage 模型。
    """
    
    def __init__(self, media_handler: MediaHandler):
        self.media_handler = media_handler
    
    def convert(self, raw_msg: Any, chat_name: str, is_group: bool = False) -> BaseMessage:
        """
        将 wxautox4 消息转换为 BaseMessage
        
        Args:
            raw_msg: wxautox4 的原始消息对象
            chat_name: 聊天对象名称
            is_group: 是否群聊
            
        Returns:
            转换后的 BaseMessage 对象
        """
        try:
            # 延迟导入，避免在未安装时报错
            from wxautox4.msgs import (
                FriendMessage,
                SelfMessage,
            )
            
            # 获取消息类型
            msg_type = getattr(raw_msg, 'type', 'unknown')
            sender = getattr(raw_msg, 'sender', chat_name)
            content = getattr(raw_msg, 'content', '')
            
            # 判断是否自己发送
            is_self = isinstance(raw_msg, SelfMessage) if hasattr(raw_msg, '__class__') else False
            
            # 根据消息类型创建对应的消息对象
            if msg_type == 'text' or msg_type == 'friend':
                return self._convert_text_message(raw_msg, sender, chat_name, is_group, is_self)
            elif msg_type == 'image':
                return self._convert_image_message(raw_msg, sender, chat_name, is_group, is_self)
            elif msg_type == 'voice':
                return self._convert_voice_message(raw_msg, sender, chat_name, is_group, is_self)
            elif msg_type == 'video':
                return self._convert_video_message(raw_msg, sender, chat_name, is_group, is_self)
            elif msg_type == 'file':
                return self._convert_file_message(raw_msg, sender, chat_name, is_group, is_self)
            else:
                # 尝试通过类名判断
                return self._convert_by_class_name(raw_msg, sender, chat_name, is_group, is_self)
                
        except Exception as e:
            LOG.error(f"Failed to convert message: {e}")
            return UnknownMessage(
                sender=chat_name,
                chat_id=chat_name,
                is_group=is_group,
                content=str(raw_msg),
                raw_data=raw_msg,
            )
    
    def _convert_by_class_name(
        self, 
        raw_msg: Any, 
        sender: str, 
        chat_name: str, 
        is_group: bool,
        is_self: bool
    ) -> BaseMessage:
        """通过类名判断消息类型"""
        try:
            from wxautox4.msgs import ImageMessage as WxImageMessage
            from wxautox4.msgs import VoiceMessage as WxVoiceMessage
            from wxautox4.msgs import VideoMessage as WxVideoMessage
            
            class_name = raw_msg.__class__.__name__
            
            if isinstance(raw_msg, WxImageMessage) or 'Image' in class_name:
                return self._convert_image_message(raw_msg, sender, chat_name, is_group, is_self)
            elif isinstance(raw_msg, WxVoiceMessage) or 'Voice' in class_name:
                return self._convert_voice_message(raw_msg, sender, chat_name, is_group, is_self)
            elif isinstance(raw_msg, WxVideoMessage) or 'Video' in class_name:
                return self._convert_video_message(raw_msg, sender, chat_name, is_group, is_self)
            else:
                # 默认作为文本消息处理
                return self._convert_text_message(raw_msg, sender, chat_name, is_group, is_self)
        except ImportError:
            # 如果导入失败，作为文本消息处理
            return self._convert_text_message(raw_msg, sender, chat_name, is_group, is_self)
    
    def _convert_text_message(
        self, 
        raw_msg: Any, 
        sender: str, 
        chat_name: str, 
        is_group: bool,
        is_self: bool
    ) -> TextMessage:
        """转换文本消息"""
        content = getattr(raw_msg, 'content', str(raw_msg))
        return TextMessage(
            sender=sender,
            chat_id=chat_name,
            is_group=is_group,
            is_self=is_self,
            content=content,
            raw_data=raw_msg,
        )
    
    def _convert_image_message(
        self, 
        raw_msg: Any, 
        sender: str, 
        chat_name: str, 
        is_group: bool,
        is_self: bool
    ) -> ImageMessage:
        """转换图片消息"""
        # 创建下载函数闭包
        def download_func(save_dir: Optional[str] = None) -> Optional[str]:
            try:
                if hasattr(raw_msg, 'download'):
                    return raw_msg.download(save_dir) if save_dir else raw_msg.download()
                elif hasattr(raw_msg, 'save'):
                    return raw_msg.save(save_dir) if save_dir else raw_msg.save()
            except Exception as e:
                LOG.error(f"Failed to download image: {e}")
            return None
        
        return ImageMessage(
            sender=sender,
            chat_id=chat_name,
            is_group=is_group,
            is_self=is_self,
            _download_func=download_func,
            raw_data=raw_msg,
        )
    
    def _convert_voice_message(
        self, 
        raw_msg: Any, 
        sender: str, 
        chat_name: str, 
        is_group: bool,
        is_self: bool
    ) -> VoiceMessage:
        """转换语音消息"""
        # 创建下载函数闭包
        def download_func(save_dir: Optional[str] = None) -> Optional[str]:
            try:
                if hasattr(raw_msg, 'download'):
                    return raw_msg.download(save_dir) if save_dir else raw_msg.download()
            except Exception as e:
                LOG.error(f"Failed to download voice: {e}")
            return None
        
        # 创建语音转文字函数闭包
        def to_text_func() -> Optional[str]:
            try:
                if hasattr(raw_msg, 'to_text'):
                    return raw_msg.to_text()
            except Exception as e:
                LOG.error(f"Failed to convert voice to text: {e}")
            return None
        
        return VoiceMessage(
            sender=sender,
            chat_id=chat_name,
            is_group=is_group,
            is_self=is_self,
            _download_func=download_func,
            _to_text_func=to_text_func,
            raw_data=raw_msg,
        )
    
    def _convert_video_message(
        self, 
        raw_msg: Any, 
        sender: str, 
        chat_name: str, 
        is_group: bool,
        is_self: bool
    ) -> VideoMessage:
        """转换视频消息"""
        def download_func(save_dir: Optional[str] = None) -> Optional[str]:
            try:
                if hasattr(raw_msg, 'download'):
                    return raw_msg.download(save_dir) if save_dir else raw_msg.download()
            except Exception as e:
                LOG.error(f"Failed to download video: {e}")
            return None
        
        return VideoMessage(
            sender=sender,
            chat_id=chat_name,
            is_group=is_group,
            is_self=is_self,
            _download_func=download_func,
            raw_data=raw_msg,
        )
    
    def _convert_file_message(
        self, 
        raw_msg: Any, 
        sender: str, 
        chat_name: str, 
        is_group: bool,
        is_self: bool
    ) -> FileMessage:
        """转换文件消息"""
        def download_func(save_dir: Optional[str] = None) -> Optional[str]:
            try:
                if hasattr(raw_msg, 'download'):
                    return raw_msg.download(save_dir) if save_dir else raw_msg.download()
            except Exception as e:
                LOG.error(f"Failed to download file: {e}")
            return None
        
        file_name = getattr(raw_msg, 'file_name', None) or getattr(raw_msg, 'filename', None)
        
        return FileMessage(
            sender=sender,
            chat_id=chat_name,
            is_group=is_group,
            is_self=is_self,
            file_name=file_name,
            _download_func=download_func,
            raw_data=raw_msg,
        )
