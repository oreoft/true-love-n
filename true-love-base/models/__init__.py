# -*- coding: utf-8 -*-
"""
Models package - 数据模型定义
"""

from models.message import (
    MessageType,
    BaseMessage,
    TextMessage,
    ImageMessage,
    VoiceMessage,
    VideoMessage,
    FileMessage,
    LinkMessage,
    ReferMessage,
    UnknownMessage,
)

from models.api import (
    ChatRequest,
    ChatResponse,
    ApiResponse,
    ApiErrors,
)

__all__ = [
    # Message models
    "MessageType",
    "BaseMessage",
    "TextMessage",
    "ImageMessage",
    "VoiceMessage",
    "VideoMessage",
    "FileMessage",
    "LinkMessage",
    "ReferMessage",
    "UnknownMessage",
    # API models
    "ChatRequest",
    "ChatResponse",
    "ApiResponse",
    "ApiErrors",
]

