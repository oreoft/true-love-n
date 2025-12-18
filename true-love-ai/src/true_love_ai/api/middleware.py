#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中间件模块
日志、计时
"""
import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

LOG = logging.getLogger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    """请求计时中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        response.headers["X-Process-Time"] = f"{process_time:.0f}ms"
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 请求日志
        body = b""
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
        
        LOG.info(
            f"Request: [{request.method} {request.url.path}], "
            f"req: [{body.decode()[:200] if body else 'empty'}]"
        )
        
        # 处理请求
        response = await call_next(request)
        
        # 响应日志
        LOG.info(
            f"Response: [{request.method} {request.url.path}, "
            f"cost: {response.headers.get('X-Process-Time', 'N/A')}]"
        )
        
        return response
