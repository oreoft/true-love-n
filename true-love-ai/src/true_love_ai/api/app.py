#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 应用模块
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from true_love_ai.api.routes import router
from true_love_ai.api.middleware import LoggingMiddleware, TimingMiddleware
from true_love_ai.core.config import get_config

LOG = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    LOG.info("真爱粉 AI 服务启动中...")
    yield
    LOG.info("真爱粉 AI 服务关闭中...")


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""

    application = FastAPI(
        title="True Love AI",
        description="真爱粉 AI 服务 - 你的可爱智能助手~",
        version="0.2.0",
        lifespan=lifespan
    )

    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 自定义中间件
    application.add_middleware(LoggingMiddleware)
    application.add_middleware(TimingMiddleware)

    # 注册路由
    application.include_router(router)

    # 健康检查
    @application.get("/")
    async def root():
        return "pong"

    @application.get("/ping")
    async def ping():
        return "pong"

    return application


# 创建应用实例
app = create_app()
