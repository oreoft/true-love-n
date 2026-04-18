# -*- coding: utf-8 -*-
"""
Dependencies - 依赖注入

FastAPI 依赖注入定义。
"""

from .exception_handlers import AuthException


def verify_token(token: str) -> bool:
    """验证 token"""
    from ..core import Config
    valid_tokens = Config().HTTP_TOKEN or []
    if token not in valid_tokens:
        raise AuthException("failed token check")
    return True
