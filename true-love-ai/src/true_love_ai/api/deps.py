#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""依赖注入模块"""
from true_love_ai.core.config import get_config


def verify_token(token: str) -> bool:
    config = get_config()
    if config.http is None:
        return False
    return token in config.http.token
