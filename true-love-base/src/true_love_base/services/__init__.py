# -*- coding: utf-8 -*-
"""
Services package - 业务服务层
"""

from true_love_base.services.robot import Robot
from true_love_base.services.server_client import get_chat

__all__ = [
    "Robot",
    "get_chat",
]
