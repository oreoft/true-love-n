# -*- coding: utf-8 -*-
"""
FastAPI Application - FastAPI 应用

创建和配置 FastAPI 应用实例。
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .routes import router
from .middleware import setup_middleware
from .exception_handlers import setup_exception_handlers

LOG = logging.getLogger("FastAPIApp")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    LOG.info("FastAPI 应用启动中...")
    yield
    LOG.info("FastAPI 应用关闭中...")


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    app = FastAPI(
        title="True Love Server",
        description="真爱粉服务端 - 微信机器人后端服务",
        version="0.2.0",
        lifespan=lifespan,
    )

    # 设置中间件
    setup_middleware(app)

    # 设置异常处理器
    setup_exception_handlers(app)

    # 注册路由
    app.include_router(router)

    # 根路径返回 index.html
    @app.get("/", include_in_schema=False)
    async def root():
        return FileResponse("static/index.html")

    # 挂载静态文件目录（放在最后，避免覆盖其他路由）
    app.mount("/static", StaticFiles(directory="static"), name="static")

    return app
