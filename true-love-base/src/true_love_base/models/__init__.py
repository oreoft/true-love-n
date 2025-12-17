# -*- coding: utf-8 -*-
"""
Models package - 数据模型定义
"""

from true_love_base.models.message import (
    ChatMessage,
    ImageMsg,
    VoiceMsg,
    VideoMsg,
    FileMsg,
    LinkMsg,
)

from true_love_base.models.api import (
    ChatRequest,
    ChatResponse,
    ApiResponse,
    ApiErrors,
)

__all__ = [
    # Message models
    "ChatMessage",
    "ImageMsg",
    "VoiceMsg",
    "VideoMsg",
    "FileMsg",
    "LinkMsg",
    # API models
    "ChatRequest",
    "ChatResponse",
    "ApiResponse",
    "ApiErrors",
]
