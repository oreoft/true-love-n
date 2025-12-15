# -*- coding: utf-8 -*-
"""
Core package - 核心抽象层

定义微信客户端的抽象协议和核心组件。
"""

from core.client_protocol import WeChatClientProtocol, MessageCallback
from core.media_handler import MediaHandler

__all__ = [
    "WeChatClientProtocol",
    "MessageCallback",
    "MediaHandler",
]

