# -*- coding: utf-8 -*-
"""
Main Entry Point - 主入口

启动真爱粉服务端。
"""

import signal
import logging

import uvicorn

from .services import base_client
from .jobs import Job
from .api import create_app
from .core import Config
from .core.db_engine import init_db

LOG = logging.getLogger("Main")
config = Config()


def notice_master():
    """启动通知和信号处理"""
    master = config.BASE_SERVER.get("master_name")
    base_client.send_text(master, "", "真爱粉server启动成功...")

    def handler(sig, frame):
        """退出前清理环境"""
        base_client.send_text(master, "", "真爱粉server正在关闭...")
        exit(0)

    signal.signal(signal.SIGINT, handler)


def main():
    """主函数"""
    init_db()

    # 通知 master
    notice_master()

    # 注册并异步启动定时任务
    if config.APP_ENV == "prod":
        job = Job()
        job.async_enable_jobs()

    # 启动持久化调度器
    from .services.scheduler_service import start_scheduler
    start_scheduler()

    # 启动应用
    app = create_app()

    # 获取 HTTP 配置
    http_config = config.HTTP or {}
    host = http_config.get("host", "0.0.0.0")
    port = http_config.get("port", 8088)

    LOG.info("启动 FastAPI 服务: %s:%s", host, port)

    # 启动 FastAPI（使用 uvicorn）
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=False,  # 使用自定义日志中间件，关闭 uvicorn 访问日志
    )


if __name__ == '__main__':
    main()
