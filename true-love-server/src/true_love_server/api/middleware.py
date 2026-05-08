# -*- coding: utf-8 -*-
"""Middleware - 中间件"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from true_love_common.integrations.fastapi import HttpLoggingMiddleware

RequestLoggingMiddleware = HttpLoggingMiddleware


def setup_middleware(app: FastAPI):
    """设置所有中间件"""
    # CORS 中间件（允许跨域）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(
        HttpLoggingMiddleware,
        service_name="tl-server",
        skip_paths={"/health", "/ping", "/admin/loki/logs"},
        max_response_body_chars=200,
    )
