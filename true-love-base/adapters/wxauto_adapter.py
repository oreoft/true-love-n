# -*- coding: utf-8 -*-
"""
WxAuto Adapter - wxautox4 SDK 适配器

实现 WeChatClientProtocol 接口，封装 wxautox4 的具体调用。
"""

import logging
from typing import Any, Callable, Optional
from axautox4x.wxautox4x import WeChat
from core.client_protocol import WeChatClientProtocol, MessageCallback
from core.media_handler import MediaHandler
from models.message import (
    BaseMessage,
    TextMessage,
    ImageMessage,
    VoiceMessage,
    VideoMessage,
    FileMessage,
    LinkMessage,
    ReferMessage,
    UnknownMessage,
    MessageType,
)

LOG = logging.getLogger("WxAutoAdapter")


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


class WxAutoClient(WeChatClientProtocol):
    """
    wxautox4 客户端适配器
    
    实现 WeChatClientProtocol 接口，封装 wxautox4 的所有操作。
    """
    
    def __init__(self):
        """初始化 wxautox4 客户端"""
        self._wx = None
        self._running = False
        self._listeners: dict[str, MessageCallback] = {}
        self._media_handler = MediaHandler()
        self._converter = WxAutoMessageConverter(self._media_handler)
        self._self_name: Optional[str] = None
        
        self._init_client()
    
    def _init_client(self):
        """初始化 wxautox4 WeChat 实例"""
        try:
            self._wx = WeChat()
            self._running = True
            LOG.info("WxAutoClient initialized successfully")
        except Exception as e:
            LOG.error(f"Failed to initialize WxAutoClient: {e}")
            raise RuntimeError(f"Failed to initialize wxautox4: {e}")
    
    @property
    def wx(self):
        """获取底层 WeChat 实例"""
        if self._wx is None:
            raise RuntimeError("WeChat client not initialized")
        return self._wx
    
    # ==================== 账号信息 ====================
    
    def get_self_id(self) -> str:
        """获取当前登录账号ID（wxautox4 可能不支持，返回昵称）"""
        return self.get_self_name()
    
    def get_self_name(self) -> str:
        """获取当前登录账号昵称"""
        if self._self_name is None:
            try:
                # wxautox4 获取昵称的方式
                self._self_name = getattr(self.wx, 'nickname', None) or "Unknown"
            except Exception as e:
                LOG.warning(f"Failed to get self name: {e}")
                self._self_name = "Unknown"
        return self._self_name
    
    # ==================== 消息发送 ====================
    
    def send_text(self, receiver: str, content: str, at_list: Optional[list[str]] = None) -> bool:
        """发送文本消息"""
        try:
            # 构建@内容
            if at_list:
                at_str = " ".join([f"@{name}" for name in at_list])
                content = f"{at_str}\n{content}"
            
            self.wx.SendMsg(content, receiver)
            LOG.info(f"Sent text to [{receiver}]: {content[:50]}...")
            return True
        except Exception as e:
            LOG.error(f"Failed to send text to [{receiver}]: {e}")
            return False
    
    def send_image(self, receiver: str, image_path: str) -> bool:
        """发送图片"""
        try:
            self.wx.SendFiles(image_path, receiver)
            LOG.info(f"Sent image to [{receiver}]: {image_path}")
            return True
        except Exception as e:
            LOG.error(f"Failed to send image to [{receiver}]: {e}")
            return False
    
    def send_file(self, receiver: str, file_path: str) -> bool:
        """发送文件"""
        try:
            self.wx.SendFiles(file_path, receiver)
            LOG.info(f"Sent file to [{receiver}]: {file_path}")
            return True
        except Exception as e:
            LOG.error(f"Failed to send file to [{receiver}]: {e}")
            return False
    
    # ==================== 消息监听 ====================
    
    def add_message_listener(self, chat_name: str, callback: MessageCallback) -> bool:
        """添加消息监听器"""
        try:
            # 创建内部回调，转换消息格式
            def internal_callback(raw_msg, chat):
                try:
                    # 判断是否群聊（简单通过名称判断，可以优化）
                    is_group = self._is_group_chat(chat_name)
                    
                    # 转换消息
                    message = self._converter.convert(raw_msg, chat_name, is_group)
                    
                    # 检测是否@了自己
                    if is_group and hasattr(raw_msg, 'content'):
                        content = str(getattr(raw_msg, 'content', ''))
                        self_name = self.get_self_name()
                        message.is_at_me = f"@{self_name}" in content or '@真爱粉' in content or 'zaf' in content
                    
                    # 调用用户回调
                    callback(message, chat_name)
                except Exception as e:
                    LOG.error(f"Error in message callback for [{chat_name}]: {e}")
            
            self.wx.AddListenChat(chat_name, internal_callback)
            self._listeners[chat_name] = callback
            LOG.info(f"Added listener for [{chat_name}]")
            return True
        except Exception as e:
            LOG.error(f"Failed to add listener for [{chat_name}]: {e}")
            return False
    
    def remove_message_listener(self, chat_name: str) -> bool:
        """移除消息监听器"""
        try:
            if chat_name in self._listeners:
                # wxautox4 可能没有直接的移除方法，需要查看文档
                # 这里先从内部字典移除
                del self._listeners[chat_name]
                LOG.info(f"Removed listener for [{chat_name}]")
            return True
        except Exception as e:
            LOG.error(f"Failed to remove listener for [{chat_name}]: {e}")
            return False
    
    def start_listening(self) -> None:
        """开始消息监听（阻塞）"""
        try:
            LOG.info("Starting message listening...")
            self.wx.KeepRunning()
        except KeyboardInterrupt:
            LOG.info("Listening stopped by user")
        except Exception as e:
            LOG.error(f"Error in message listening: {e}")
    
    def _is_group_chat(self, chat_name: str) -> bool:
        """
        判断是否群聊
        
        这是一个简单实现，实际可能需要通过其他方式判断
        """
        # wxautox4 可能提供了判断方法，这里先用简单逻辑
        # 通常群聊名称更长，或者包含特定字符
        return len(chat_name) > 10 or '群' in chat_name
    
    # ==================== 联系人管理 ====================
    
    def get_contacts(self) -> dict[str, str]:
        """
        获取联系人列表
        
        Note: wxautox4 基于 UIA，可能无法直接获取完整联系人列表
        """
        try:
            # wxautox4 可能需要通过其他方式获取
            # 这里返回空字典，具体实现需要参考文档
            LOG.warning("get_contacts not fully implemented for wxautox4")
            return {}
        except Exception as e:
            LOG.error(f"Failed to get contacts: {e}")
            return {}
    
    def get_chat_members(self, chat_name: str) -> dict[str, str]:
        """
        获取群成员列表
        
        Note: wxautox4 基于 UIA，可能无法直接获取群成员
        """
        try:
            # wxautox4 可能需要通过其他方式获取
            LOG.warning("get_chat_members not fully implemented for wxautox4")
            return {}
        except Exception as e:
            LOG.error(f"Failed to get chat members for [{chat_name}]: {e}")
            return {}
    
    # ==================== 生命周期 ====================
    
    def is_running(self) -> bool:
        """检查客户端是否运行中"""
        return self._running and self._wx is not None
    
    def cleanup(self) -> None:
        """清理资源"""
        try:
            self._running = False
            self._listeners.clear()
            LOG.info("WxAutoClient cleaned up")
        except Exception as e:
            LOG.error(f"Error during cleanup: {e}")

