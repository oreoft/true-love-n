# -*- coding: utf-8 -*-
"""
Core module - 核心模块

包含配置、上下文变量、数据库引擎等基础组件。
"""

from true_love_common.observability.logging import LoggingConfig
from .configuration import Config
from .context_vars import local_msg_id
__all__ = ["LoggingConfig", "Config", "local_msg_id"]
