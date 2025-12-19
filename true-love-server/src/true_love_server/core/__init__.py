# -*- coding: utf-8 -*-
"""
Core module - 核心模块

包含配置、上下文变量、数据库引擎等基础组件。
"""

from .configuration import Config
from .context_vars import local_msg_id
from .db_engine import create_db_and_table

__all__ = ["Config", "local_msg_id", "create_db_and_table"]

