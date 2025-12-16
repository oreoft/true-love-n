# -*- coding: utf-8 -*-
"""
Chat Message Model - 聊天消息模型

定义统一的聊天消息模型，用于 server 端处理。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class MsgType(Enum):
    """消息类型枚举"""
    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"
    VIDEO = "video"
    FILE = "file"
    LINK = "link"
    UNKNOWN = "unknown"


@dataclass
class ChatMsg:
    """
    聊天消息模型
    
    统一的消息结构，用于 server 端处理各类消息。
    """
    msg_type: MsgType
    sender: str  # 发送者ID
    chat_id: str  # 聊天ID（好友ID或群ID）
    content: str = ""  # 消息内容
    is_group: bool = False  # 是否群消息
    file_path: Optional[str] = None  # 文件路径（图片、语音、视频等）
    voice_text: Optional[str] = None  # 语音转文字内容
    refer_msg: Optional[dict] = None  # 引用消息

    def from_group(self) -> bool:
        """是否来自群聊"""
        return self.is_group

    def is_text(self) -> bool:
        """是否文本消息"""
        return self.msg_type == MsgType.TEXT

    def is_image(self) -> bool:
        """是否图片消息"""
        return self.msg_type == MsgType.IMAGE

    def is_voice(self) -> bool:
        """是否语音消息"""
        return self.msg_type == MsgType.VOICE

    def is_video(self) -> bool:
        """是否视频消息"""
        return self.msg_type == MsgType.VIDEO

    def is_file(self) -> bool:
        """是否文件消息"""
        return self.msg_type == MsgType.FILE

    def is_link(self) -> bool:
        """是否链接消息"""
        return self.msg_type == MsgType.LINK

    def has_refer(self) -> bool:
        """是否有引用消息"""
        return self.refer_msg is not None and len(self.refer_msg) > 0

    def get_refer_type(self) -> Optional[MsgType]:
        """获取引用消息类型"""
        if not self.refer_msg:
            return None
        type_str = self.refer_msg.get("msg_type", "unknown")
        try:
            return MsgType(type_str)
        except ValueError:
            return MsgType.UNKNOWN

    def get_refer_content(self) -> Optional[str]:
        """获取引用消息内容"""
        if not self.refer_msg:
            return None
        return self.refer_msg.get("content")

    def get_refer_file_path(self) -> Optional[str]:
        """获取引用消息的文件路径"""
        if not self.refer_msg:
            return None
        return self.refer_msg.get("file_path")

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "msg_type": self.msg_type.value,
            "sender": self.sender,
            "chat_id": self.chat_id,
            "content": self.content,
            "is_group": self.is_group,
            "file_path": self.file_path,
            "voice_text": self.voice_text,
            "refer_msg": self.refer_msg,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChatMsg":
        """从字典创建实例"""
        msg_type_str = data.get("msg_type", "unknown")
        try:
            msg_type = MsgType(msg_type_str)
        except ValueError:
            msg_type = MsgType.UNKNOWN

        return cls(
            msg_type=msg_type,
            sender=data.get("sender", ""),
            chat_id=data.get("chat_id", ""),
            content=data.get("content", ""),
            is_group=data.get("is_group", False),
            file_path=data.get("file_path"),
            voice_text=data.get("voice_text"),
            refer_msg=data.get("refer_msg"),
        )
