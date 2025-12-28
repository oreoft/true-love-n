# -*- coding: utf-8 -*-
"""
Dependencies - 依赖注入

FastAPI 依赖注入定义。
"""

from functools import lru_cache
from typing import Any

from fastapi import Request, Body

from .exception_handlers import AuthException


async def verify_token(request: Request, body: dict = Body(...)) -> bool:
    """
    验证 token
    
    从请求 body 中获取 token 并验证。
    """
    from ..core import Config
    http_config = Config().HTTP_TOKEN or {}

    token = body.get('token')
    valid_tokens = http_config.get("token", [])

    if token not in valid_tokens:
        raise AuthException("failed token check")

    return True


@lru_cache()
def get_msg_handler():
    """
    获取消息处理器实例（单例）
    """
    from ..handlers import MsgHandler
    return MsgHandler()
