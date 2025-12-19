# -*- coding: utf-8 -*-
"""
True Love Server - 真爱粉服务端

微信机器人后端服务，处理消息和定时任务。
"""

__version__ = "0.2.0"

from .core import Config, local_msg_id, create_db_and_table
from .models import ChatMsg
from .api import create_app

__all__ = [
    "__version__",
    "Config",
    "local_msg_id",
    "create_db_and_table",
    "ChatMsg",
    "create_app",
]
