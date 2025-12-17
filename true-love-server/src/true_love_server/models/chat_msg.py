# -*- coding: utf-8 -*-
"""
消息模型 - Server 端

与 Base 端结构一致的统一消息模型。
"""

from dataclasses import dataclass
from typing import Optional, Any


@dataclass
class ImageMsg:
    """图片消息数据"""
    file_path: Optional[str] = None


@dataclass
class VoiceMsg:
    """语音消息数据"""
    text_content: Optional[str] = None


@dataclass
class VideoMsg:
    """视频消息数据"""
    file_path: Optional[str] = None


@dataclass
class FileMsg:
    """文件消息数据"""
    file_path: Optional[str] = None
    file_name: Optional[str] = None


@dataclass
class LinkMsg:
    """链接消息数据"""
    url: Optional[str] = None


@dataclass
class ChatMsg:
    """
    统一消息模型
    
    与 Base 端的 ChatMessage 结构一致。
    """
    # ===== 通用字段 =====
    msg_type: str
    sender: str
    chat_id: str
    content: str = ""
    is_group: bool = False
    is_self: bool = False
    is_at_me: bool = False
    
    # ===== 类型特有字段（按需填充，其他为 None）=====
    image_msg: Optional[ImageMsg] = None
    voice_msg: Optional[VoiceMsg] = None
    video_msg: Optional[VideoMsg] = None
    file_msg: Optional[FileMsg] = None
    link_msg: Optional[LinkMsg] = None
    refer_msg: Optional['ChatMsg'] = None

    # ===== 类型判断便捷方法 =====
    
    def is_text(self) -> bool:
        """是否文本消息"""
        return self.msg_type == 'text'
    
    def is_image(self) -> bool:
        """是否图片消息"""
        return self.msg_type == 'image'
    
    def is_voice(self) -> bool:
        """是否语音消息"""
        return self.msg_type == 'voice'
    
    def is_video(self) -> bool:
        """是否视频消息"""
        return self.msg_type == 'video'
    
    def is_file(self) -> bool:
        """是否文件消息"""
        return self.msg_type == 'file'
    
    def is_link(self) -> bool:
        """是否链接消息"""
        return self.msg_type == 'link'
    
    def has_refer(self) -> bool:
        """是否有引用消息"""
        return self.refer_msg is not None
    
    def from_group(self) -> bool:
        """是否来自群聊"""
        return self.is_group

    # ===== 便捷取值属性（兼容旧代码）=====
    
    @property
    def file_path(self) -> Optional[str]:
        """获取文件路径（图片/视频/文件）"""
        if self.image_msg and self.image_msg.file_path:
            return self.image_msg.file_path
        if self.video_msg and self.video_msg.file_path:
            return self.video_msg.file_path
        if self.file_msg and self.file_msg.file_path:
            return self.file_msg.file_path
        return None
    
    @property
    def voice_text(self) -> Optional[str]:
        """获取语音转文字"""
        return self.voice_msg.text_content if self.voice_msg else None
    
    @property
    def url(self) -> Optional[str]:
        """获取链接"""
        return self.link_msg.url if self.link_msg else None

    # ===== 引用消息便捷方法 =====
    
    def get_refer_type(self) -> Optional[str]:
        """获取引用消息类型"""
        return self.refer_msg.msg_type if self.refer_msg else None
    
    def get_refer_content(self) -> Optional[str]:
        """获取引用消息内容"""
        return self.refer_msg.content if self.refer_msg else None
    
    def get_refer_file_path(self) -> Optional[str]:
        """获取引用消息的文件路径"""
        if not self.refer_msg:
            return None
        return self.refer_msg.file_path  # 复用 property

    # ===== 序列化/反序列化 =====
    
    @classmethod
    def from_dict(cls, data: dict) -> "ChatMsg":
        """从字典创建实例"""
        return cls(
            msg_type=data.get("msg_type", "text"),
            sender=data.get("sender", ""),
            chat_id=data.get("chat_id", ""),
            content=data.get("content", ""),
            is_group=data.get("is_group", False),
            is_self=data.get("is_self", False),
            is_at_me=data.get("is_at_me", False),
            image_msg=ImageMsg(**data["image_msg"]) if data.get("image_msg") else None,
            voice_msg=VoiceMsg(**data["voice_msg"]) if data.get("voice_msg") else None,
            video_msg=VideoMsg(**data["video_msg"]) if data.get("video_msg") else None,
            file_msg=FileMsg(**data["file_msg"]) if data.get("file_msg") else None,
            link_msg=LinkMsg(**data["link_msg"]) if data.get("link_msg") else None,
            refer_msg=cls.from_dict(data["refer_msg"]) if data.get("refer_msg") else None,
        )
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        from dataclasses import asdict
        return asdict(self)
