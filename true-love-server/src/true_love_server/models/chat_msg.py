# -*- coding: utf-8 -*-
"""
消息模型 - Server 端

通用消息结构，支持多平台（wechat / lark / ...）。
"""

from dataclasses import dataclass, asdict
from typing import Optional, Any


# ==================== 资源引用 ====================

@dataclass
class ResourceRef:
    """统一资源引用：本地路径 或 HTTP URL"""
    ref: str                    # 本地路径 或 HTTP URL
    source: str = "local"       # "local" | "url"

    @classmethod
    def from_dict(cls, data: dict) -> "ResourceRef":
        return cls(ref=data.get("ref", ""), source=data.get("source", "local"))


# ==================== 媒体消息子类型 ====================

@dataclass
class ImageMsg:
    resource: Optional[ResourceRef] = None

    @classmethod
    def from_dict(cls, data: dict) -> "ImageMsg":
        resource = ResourceRef.from_dict(data["resource"]) if data.get("resource") else None
        return cls(resource=resource)


@dataclass
class VoiceMsg:
    text_content: Optional[str] = None
    resource: Optional[ResourceRef] = None

    @classmethod
    def from_dict(cls, data: dict) -> "VoiceMsg":
        resource = ResourceRef.from_dict(data["resource"]) if data.get("resource") else None
        return cls(text_content=data.get("text_content"), resource=resource)


@dataclass
class VideoMsg:
    resource: Optional[ResourceRef] = None

    @classmethod
    def from_dict(cls, data: dict) -> "VideoMsg":
        resource = ResourceRef.from_dict(data["resource"]) if data.get("resource") else None
        return cls(resource=resource)


@dataclass
class FileMsg:
    file_name: Optional[str] = None
    resource: Optional[ResourceRef] = None

    @classmethod
    def from_dict(cls, data: dict) -> "FileMsg":
        resource = ResourceRef.from_dict(data["resource"]) if data.get("resource") else None
        return cls(file_name=data.get("file_name"), resource=resource)


@dataclass
class LinkMsg:
    url: Optional[str] = None
    title: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "LinkMsg":
        return cls(url=data.get("url"), title=data.get("title"))


# ==================== 主消息体 ====================

@dataclass
class ChatMsg:
    """通用消息模型，支持多平台。"""

    # 平台标识
    platform: str = "wechat"            # "wechat" | "lark"

    # 消息元信息
    msg_type: str = "text"              # text/image/voice/video/file/link/unknown
    msg_id: str = ""
    msg_hash: str = ""

    # 发送者（两个字段都尽量填）
    sender_id: str = ""                 # 平台唯一 ID（open_id / wxid）；微信暂时用昵称填
    sender_name: str = ""               # 昵称/显示名；可为空

    # 会话
    chat_id: str = ""                   # 平台唯一会话 ID；微信暂时用群名填
    chat_name: str = ""                 # 群名 / 好友名（显示用，可为空）
    is_group: bool = False

    # 标志位
    is_self: bool = False
    is_at_me: bool = False

    # 消息内容
    content: str = ""
    image_msg: Optional[ImageMsg] = None
    voice_msg: Optional[VoiceMsg] = None
    video_msg: Optional[VideoMsg] = None
    file_msg: Optional[FileMsg] = None
    link_msg: Optional[LinkMsg] = None
    refer_msg: Optional['ChatMsg'] = None   # 引用/回复消息（最多一层）

    # ==================== 便捷属性 ====================

    @property
    def effective_sender_id(self) -> str:
        return self.sender_id

    @property
    def effective_chat_id(self) -> str:
        return self.chat_id

    def is_text(self) -> bool:
        return self.msg_type == "text"

    def is_image(self) -> bool:
        return self.msg_type == "image"

    def is_voice(self) -> bool:
        return self.msg_type == "voice"

    def is_video(self) -> bool:
        return self.msg_type == "video"

    def is_file(self) -> bool:
        return self.msg_type == "file"

    def is_link(self) -> bool:
        return self.msg_type == "link"

    def has_refer(self) -> bool:
        return self.refer_msg is not None

    @property
    def voice_text(self) -> Optional[str]:
        return self.voice_msg.text_content if self.voice_msg else None

    @property
    def url(self) -> Optional[str]:
        return self.link_msg.url if self.link_msg else None

    # ==================== 序列化 ====================

    @classmethod
    def from_dict(cls, data: dict) -> "ChatMsg":
        sender_id = data.get("sender_id", "")
        sender_name = data.get("sender_name", "")

        # chat_name 兼容：旧版 chat_id 就是群名
        chat_id = data.get("chat_id", "")
        chat_name = data.get("chat_name") or chat_id

        return cls(
            platform=data.get("platform", "wechat"),
            msg_type=data.get("msg_type", "text"),
            msg_id=data.get("msg_id", ""),
            msg_hash=data.get("msg_hash", ""),
            sender_id=sender_id,
            sender_name=sender_name,
            chat_id=chat_id,
            chat_name=chat_name,
            is_group=data.get("is_group", False),
            is_self=data.get("is_self", False),
            is_at_me=data.get("is_at_me", False),
            content=data.get("content", ""),
            image_msg=ImageMsg.from_dict(data["image_msg"]) if data.get("image_msg") else None,
            voice_msg=VoiceMsg.from_dict(data["voice_msg"]) if data.get("voice_msg") else None,
            video_msg=VideoMsg.from_dict(data["video_msg"]) if data.get("video_msg") else None,
            file_msg=FileMsg.from_dict(data["file_msg"]) if data.get("file_msg") else None,
            link_msg=LinkMsg.from_dict(data["link_msg"]) if data.get("link_msg") else None,
            refer_msg=cls.from_dict(data["refer_msg"]) if data.get("refer_msg") else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
