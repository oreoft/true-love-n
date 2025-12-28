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
    
    # 不记录日志的路径
    SKIP_LOG_PATHS = {"/logs", "/health"}
    # 响应日志最大长度
    MAX_RESP_LOG_LEN = 200
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 检查是否跳过日志
        skip_log = request.url.path in self.SKIP_LOG_PATHS
        
        # 请求日志
        body = b""
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
        
        if not skip_log:
            LOG.info(
                f"AI服务收到请求: [{request.method} {request.url.path}], "
                f"req: [{body.decode()[:2000] if body else 'empty'}]"
            )
        
        # 处理请求
        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        
        # 读取响应体
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk
        
        if not skip_log:
            # 响应日志 - 对二进制响应不尝试解码
            if response.media_type and response.media_type.startswith(("video/", "image/", "audio/")):
                resp_log = f"[binary {response.media_type}, {len(response_body)} bytes]"
            else:
                try:
                    resp_text = response_body.decode() if response_body else 'empty'
                    # 截断过长的响应（可能包含 base64 等大数据）
                    if len(resp_text) > self.MAX_RESP_LOG_LEN:
                        resp_log = f"{resp_text[:self.MAX_RESP_LOG_LEN]}...[truncated, total {len(resp_text)} chars]"
                    else:
                        resp_log = resp_text
                except UnicodeDecodeError:
                    resp_log = f"[binary data, {len(response_body)} bytes]"
            
            LOG.info(
                f"AI服务返回响应: [{request.method} {request.url.path}], "
                f"cost: {process_time:.0f}ms, "
                f"resp: [{resp_log}]"
            )
        
        # 重新构建响应（因为body_iterator已被消费）
        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )
