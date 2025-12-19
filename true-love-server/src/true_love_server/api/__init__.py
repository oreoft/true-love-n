# -*- coding: utf-8 -*-
"""
API module - HTTP 接口模块

基于 FastAPI 的 HTTP 服务。
"""

from .app import create_app

__all__ = ["create_app"]
