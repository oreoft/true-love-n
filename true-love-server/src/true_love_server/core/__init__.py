# -*- coding: utf-8 -*-
"""
Core module - 核心模块

包含配置、数据库引擎等基础组件。
"""

from true_love_common.observability.logging import LoggingConfig
from .configuration import Config

__all__ = ["LoggingConfig", "Config"]
