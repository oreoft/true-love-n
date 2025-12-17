# -*- coding: utf-8 -*-
"""
Message Converter - wxautox4 消息转换器

将 wxautox4 的消息对象转换为统一的 BaseMessage 模型。
使用类级别缓存优化导入性能。
"""

import logging
from typing import Any, Optional, Type

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
    使用类级别缓存，避免每次转换都重新导入 wxautox4 消息类。
    """
    
    # 类级别缓存：wxautox4 消息类
    _wx_classes_loaded: bool = False
    _FriendMessage: Optional[Type] = None
    _SelfMessage: Optional[Type] = None
    _WxImageMessage: Optional[Type] = None
    _WxVoiceMessage: Optional[Type] = None
    _WxVideoMessage: Optional[Type] = None
    
    def __init__(self, media_handler: MediaHandler):
        self.media_handler = media_handler
        # 在初始化时加载 wxautox4 消息类
        self._load_wx_classes()
    
    @classmethod
    def _load_wx_classes(cls) -> None:
        """
        一次性加载 wxautox4 消息类（类级别缓存）
        
        避免每次消息转换都重新导入，提升性能。
        """
        if cls._wx_classes_loaded:
            return
        
        try:
            from wxautox4.msgs import (
                FriendMessage,
                SelfMessage,
            )
            cls._FriendMessage = FriendMessage
            cls._SelfMessage = SelfMessage
            LOG.debug("Loaded wxautox4 basic message classes")
        except ImportError as e:
            LOG.warning(f"Failed to import wxautox4 basic message classes: {e}")
        
        try:
            from wxautox4.msgs import (
                ImageMessage as WxImageMessage,
                VoiceMessage as WxVoiceMessage,
                VideoMessage as WxVideoMessage,
            )
            cls._WxImageMessage = WxImageMessage
            cls._WxVoiceMessage = WxVoiceMessage
            cls._WxVideoMessage = WxVideoMessage
            LOG.debug("Loaded wxautox4 media message classes")
        except ImportError as e:
            LOG.warning(f"Failed to import wxautox4 media message classes: {e}")
        
        cls._wx_classes_loaded = True
        LOG.info("WxAutoMessageConverter: wxautox4 classes loaded")
    
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
            # 获取消息类型
            msg_type = getattr(raw_msg, 'type', 'unknown')
            sender = getattr(raw_msg, 'sender', chat_name)
            
            # 如果 sender 是 wxauto 的消息属性标识（'friend'/'self'），用 chat_name 替代
            if sender in ('friend', 'self', ''):
                sender = chat_name
            
            # 判断是否自己发送（使用缓存的类）
            is_self = False
            if self._SelfMessage is not None:
                is_self = isinstance(raw_msg, self._SelfMessage)
            
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
        """通过类名判断消息类型（使用缓存的类）"""
        class_name = raw_msg.__class__.__name__
        
        # 使用缓存的类进行类型判断
        if self._WxImageMessage is not None and isinstance(raw_msg, self._WxImageMessage):
            return self._convert_image_message(raw_msg, sender, chat_name, is_group, is_self)
        elif self._WxVoiceMessage is not None and isinstance(raw_msg, self._WxVoiceMessage):
            return self._convert_voice_message(raw_msg, sender, chat_name, is_group, is_self)
        elif self._WxVideoMessage is not None and isinstance(raw_msg, self._WxVideoMessage):
            return self._convert_video_message(raw_msg, sender, chat_name, is_group, is_self)
        elif 'Image' in class_name:
            return self._convert_image_message(raw_msg, sender, chat_name, is_group, is_self)
        elif 'Voice' in class_name:
            return self._convert_voice_message(raw_msg, sender, chat_name, is_group, is_self)
        elif 'Video' in class_name:
            return self._convert_video_message(raw_msg, sender, chat_name, is_group, is_self)
        else:
            # 默认作为文本消息处理
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
                LOG.info(f"Downloading image to: {save_dir}")
                if hasattr(raw_msg, 'download'):
                    result = raw_msg.download(save_dir) if save_dir else raw_msg.download()
                    LOG.info(f"Download result: {result}, type: {type(result)}")
                    return str(result) if result else None
                elif hasattr(raw_msg, 'save'):
                    result = raw_msg.save(save_dir) if save_dir else raw_msg.save()
                    LOG.info(f"Save result: {result}, type: {type(result)}")
                    return str(result) if result else None
            except Exception as e:
                LOG.error(f"Failed to download image: {e}", exc_info=True)
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
        """
        转换语音消息
        
        直接调用 wxauto 的 to_text() 方法获取语音转文字结果。
        注意：VoiceMessage 没有 download() 方法，语音只能通过微信自带的转文字功能处理。
        """
        text_content = None
        try:
            if hasattr(raw_msg, 'to_text'):
                text_content = raw_msg.to_text()
                LOG.info(f"Voice to_text success: {text_content}")
        except Exception as e:
            LOG.warning(f"Voice to_text failed: {e}")
        
        return VoiceMessage(
            sender=sender,
            chat_id=chat_name,
            is_group=is_group,
            is_self=is_self,
            text_content=text_content,
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
