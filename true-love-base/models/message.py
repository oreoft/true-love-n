# -*- coding: utf-8 -*-
"""
Message Models - 消息数据模型

定义统一的消息模型，与底层SDK解耦。
所有消息类型都继承自 BaseMessage，提供统一的接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import json


class MessageType(Enum):
    """消息类型枚举"""
    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"
    VIDEO = "video"
    FILE = "file"
    LINK = "link"
    REFER = "refer"  # 引用消息
    UNKNOWN = "unknown"


@dataclass
class BaseMessage(ABC):
    """
    消息基类
    
    所有消息类型的抽象基类，定义统一的消息接口。
    """
    msg_type: MessageType
    sender: str  # 发送者ID或昵称
    chat_id: str  # 聊天ID（好友ID或群ID）
    is_group: bool = False  # 是否群消息
    is_self: bool = False  # 是否自己发送
    is_at_me: bool = False  # 是否@了我
    timestamp: Optional[float] = None  # 消息时间戳
    raw_data: Any = None  # 原始消息数据，用于调试

    @abstractmethod
    def get_content(self) -> str:
        """获取消息的文本内容"""
        pass

    def to_dict(self) -> dict[str, Any]:
        """转换为字典，用于JSON序列化"""
        return {
            "msg_type": self.msg_type.value,
            "sender": self.sender,
            "chat_id": self.chat_id,
            "is_group": self.is_group,
            "is_self": self.is_self,
            "is_at_me": self.is_at_me,
            "timestamp": self.timestamp,
            "content": self.get_content(),
        }

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class TextMessage(BaseMessage):
    """文本消息"""
    msg_type: MessageType = field(default=MessageType.TEXT, init=False)
    content: str = ""

    def get_content(self) -> str:
        return self.content


@dataclass
class ImageMessage(BaseMessage):
    """图片消息"""
    msg_type: MessageType = field(default=MessageType.IMAGE, init=False)
    file_path: Optional[str] = None  # 下载后的本地路径
    _download_func: Any = field(default=None, repr=False)  # 下载函数引用

    def get_content(self) -> str:
        return self.file_path or "[Image]"

    def download(self, save_dir: Optional[str] = None) -> Optional[str]:
        """
        下载图片到本地
        
        Args:
            save_dir: 保存目录，None则使用默认目录
            
        Returns:
            下载后的文件路径，失败返回None
        """
        if self._download_func:
            self.file_path = self._download_func(save_dir)
        return self.file_path

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["file_path"] = self.file_path
        return base


@dataclass
class VoiceMessage(BaseMessage):
    """语音消息"""
    msg_type: MessageType = field(default=MessageType.VOICE, init=False)
    file_path: Optional[str] = None  # 下载后的本地路径
    text_content: Optional[str] = None  # 语音转文字内容
    duration: Optional[int] = None  # 语音时长（秒）
    _download_func: Any = field(default=None, repr=False)
    _to_text_func: Any = field(default=None, repr=False)

    def get_content(self) -> str:
        if self.text_content:
            return self.text_content
        return self.file_path or "[Voice]"

    def download(self, save_dir: Optional[str] = None) -> Optional[str]:
        """下载语音到本地"""
        if self._download_func:
            self.file_path = self._download_func(save_dir)
        return self.file_path

    def to_text(self) -> Optional[str]:
        """语音转文字"""
        if self._to_text_func:
            self.text_content = self._to_text_func()
        return self.text_content

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["file_path"] = self.file_path
        base["text_content"] = self.text_content
        base["duration"] = self.duration
        return base


@dataclass
class VideoMessage(BaseMessage):
    """视频消息"""
    msg_type: MessageType = field(default=MessageType.VIDEO, init=False)
    file_path: Optional[str] = None
    thumbnail_path: Optional[str] = None  # 缩略图路径
    duration: Optional[int] = None  # 视频时长（秒）
    _download_func: Any = field(default=None, repr=False)

    def get_content(self) -> str:
        return self.file_path or "[Video]"

    def download(self, save_dir: Optional[str] = None) -> Optional[str]:
        """下载视频到本地"""
        if self._download_func:
            self.file_path = self._download_func(save_dir)
        return self.file_path

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["file_path"] = self.file_path
        base["thumbnail_path"] = self.thumbnail_path
        base["duration"] = self.duration
        return base


@dataclass
class FileMessage(BaseMessage):
    """文件消息"""
    msg_type: MessageType = field(default=MessageType.FILE, init=False)
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None  # 文件大小（字节）
    _download_func: Any = field(default=None, repr=False)

    def get_content(self) -> str:
        return self.file_name or self.file_path or "[File]"

    def download(self, save_dir: Optional[str] = None) -> Optional[str]:
        """下载文件到本地"""
        if self._download_func:
            self.file_path = self._download_func(save_dir)
        return self.file_path

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["file_path"] = self.file_path
        base["file_name"] = self.file_name
        base["file_size"] = self.file_size
        return base


@dataclass
class LinkMessage(BaseMessage):
    """链接消息（公众号文章、分享链接等）"""
    msg_type: MessageType = field(default=MessageType.LINK, init=False)
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    thumbnail_url: Optional[str] = None

    def get_content(self) -> str:
        return self.title or self.url or "[Link]"

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["title"] = self.title
        base["description"] = self.description
        base["url"] = self.url
        base["thumbnail_url"] = self.thumbnail_url
        return base


@dataclass
class ReferMessage(BaseMessage):
    """
    引用消息
    
    包含主消息内容和被引用的消息
    """
    msg_type: MessageType = field(default=MessageType.REFER, init=False)
    content: str = ""  # 主消息文本
    referred_msg: Optional[BaseMessage] = None  # 被引用的消息

    def get_content(self) -> str:
        return self.content

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["content"] = self.content
        base["referred_msg"] = self.referred_msg.to_dict() if self.referred_msg else None
        return base


@dataclass
class UnknownMessage(BaseMessage):
    """未知类型消息"""
    msg_type: MessageType = field(default=MessageType.UNKNOWN, init=False)
    content: str = ""
    original_type: Optional[str] = None  # 原始消息类型

    def get_content(self) -> str:
        return self.content or f"[Unknown: {self.original_type}]"

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["original_type"] = self.original_type
        return base


