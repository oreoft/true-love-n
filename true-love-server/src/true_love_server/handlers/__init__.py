# -*- coding: utf-8 -*-
"""
Handlers module - 消息处理器模块

使用策略模式 + 注册表机制管理处理器。
"""

# 核心组件
from .base_handler import BaseHandler
from .registry import registry, register_handler
from .msg_handler import MsgHandler

from .image_gen_handler import ImageGenHandler
from .chat_handler import ChatHandler

__all__ = [
    # 核心
    "BaseHandler",
    "registry",
    "register_handler",
    "MsgHandler",
    # 处理器
    "ImageGenHandler",
    "ChatHandler",
]
