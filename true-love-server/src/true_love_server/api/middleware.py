# -*- coding: utf-8 -*-
"""
Middleware - 中间件

请求/响应日志记录等中间件。
"""

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

LOG = logging.getLogger("Middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next):
        # 生成请求 ID
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        
        # 记录请求开始时间
        start_time = time.time()
        
        # 获取请求体（需要缓存以便后续使用）
        body = await request.body()
        body_text = body.decode('utf-8')[:200] if body else ""
        
        LOG.info(
            "Request:[%s] [%s %s], req:[%s]",
            request_id,
            request.method,
            request.url.path,
            body_text
        )
        
        # 重新设置请求体（因为已经被读取）
        async def receive():
            return {"type": "http.request", "body": body}
        request._receive = receive
        
        # 处理请求
        response = await call_next(request)
        
        # 计算耗时
        cost = (time.time() - start_time) * 1000
        
        LOG.info(
            "Response:[%s] [%s %s, cost:%.0fms], status:[%s]",
            request_id,
            request.method,
            request.url.path,
            cost,
            response.status_code
        )
        
        return response


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
    
    app.add_middleware(RequestLoggingMiddleware)
