# -*- coding: utf-8 -*-
"""
消息模型 - 简化版

统一的消息数据结构，使用 dataclass + asdict 自动序列化。
新增字段只需要在对应的数据类中添加即可。
"""

from dataclasses import dataclass, asdict
from typing import Optional, Any


@dataclass
class ImageMsg:
    """图片消息数据"""
    file_path: Optional[str] = None


@dataclass
class VoiceMsg:
    """语音消息数据"""
    text_content: Optional[str] = None  # 语音转文字


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
class ChatMessage:
    """
    统一消息模型
    
    通用字段 + 类型特有字段（按需填充）
    msg_type: text/image/voice/video/file/link/refer
    """
    # ===== 通用字段 =====
    msg_type: str
    sender: str
    chat_id: str
    content: str = ""
    is_group: bool = False
    is_self: bool = False
    is_at_me: bool = False
    raw_msg: Any = None

    # ===== 类型特有字段（按需填充，其他为 None）=====
    image_msg: Optional[ImageMsg] = None
    voice_msg: Optional[VoiceMsg] = None
    video_msg: Optional[VideoMsg] = None
    file_msg: Optional[FileMsg] = None
    link_msg: Optional[LinkMsg] = None
    refer_msg: Optional['ChatMessage'] = None  # 引用消息（递归结构）
    
    def to_dict(self) -> dict[str, Any]:
        """
        转换为字典，用于 JSON 序列化
        
        注意：raw_msg 字段会被排除，因为它是 wxautox4 的原始消息对象，
        不可序列化，且只用于本地操作（如 quote、tickle）。
        """
        result = asdict(self)
        # 排除不可序列化的 raw_msg 字段
        result.pop('raw_msg', None)
        # 如果有引用消息，也需要排除其中的 raw_msg
        if result.get('refer_msg') and isinstance(result['refer_msg'], dict):
            result['refer_msg'].pop('raw_msg', None)
        return result
