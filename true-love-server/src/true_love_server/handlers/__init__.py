# -*- coding: utf-8 -*-
"""
Handlers module - 消息处理器模块

使用策略模式 + 注册表机制管理处理器。
"""

# 核心组件
from .base_handler import BaseHandler
from .registry import registry, register_handler
from .msg_handler import MsgHandler

# 原有的触发处理器（被新处理器包装）
from .trig_manage_handler import TrigManageHandler
from .trig_remainder_handler import TrigRemainderHandler
from .trig_search_handler import TrigSearchHandler
from .trig_task_handler import TrigTaskHandler

# 处理器（基于策略模式）
from .query_handler import QueryHandler
from .task_handler import TaskHandler
from .reminder_handler import ReminderHandler
from .admin_handler import AdminHandler
from .image_gen_handler import ImageGenHandler
from .chat_handler import ChatHandler

__all__ = [
    # 核心
    "BaseHandler",
    "registry",
    "register_handler",
    "MsgHandler",
    # 处理器
    "QueryHandler",
    "TaskHandler",
    "ReminderHandler",
    "AdminHandler",
    "ImageGenHandler",
    "ChatHandler",
    # 触发器（内部使用）
    "TrigManageHandler",
    "TrigSearchHandler",
    "TrigTaskHandler",
    "TrigRemainderHandler",
]
