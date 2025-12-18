#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心模块
配置管理、会话管理
"""
from true_love_ai.core.config import Config, get_config
from true_love_ai.core.session import SessionManager, get_session_manager

__all__ = [
    'Config',
    'get_config',
    'SessionManager',
    'get_session_manager',
]
