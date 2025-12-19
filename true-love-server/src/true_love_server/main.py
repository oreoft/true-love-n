# -*- coding: utf-8 -*-
"""
Main Entry Point - 主入口

启动真爱粉服务端。
"""

import signal
import logging
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial

import uvicorn

from .services import base_client
from .jobs import Job
from .api import create_app
from .core import Config, create_db_and_table

LOG = logging.getLogger("Main")
config = Config()


def start_static_server(port: int = 8089, directory: str = 'static'):
    """启动静态文件服务器"""
    handler = partial(SimpleHTTPRequestHandler, directory=directory)
    server = HTTPServer(("0.0.0.0", port), handler)
    LOG.info("静态页面服务启动: http://0.0.0.0:%s", port)
    server.serve_forever()


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
    # 初始化数据库
    create_db_and_table()

    # 通知 master
    notice_master()

    # 注册并异步启动定时任务
    job = Job()
    job.async_enable_jobs()

    # 启动静态页面服务器（独立线程）
    static_thread = threading.Thread(target=start_static_server, args=(8089, 'static'), daemon=True)
    static_thread.start()

    # 创建 FastAPI 应用
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
    )


if __name__ == '__main__':
    main()
