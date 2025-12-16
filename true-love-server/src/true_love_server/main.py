# -*- coding: utf-8 -*-
"""
Main Entry Point - 主入口

启动真爱粉服务端。
"""

import signal

from .services import base_client
from .jobs import Job
from . import server
from .core import Config, create_db_and_table

config = Config()


def notice_master():
    # 启动的通知（使用昵称而非 wxid）
    master = config.BASE_SERVER.get("master_name") or config.BASE_SERVER.get("master_wxid")
    base_client.send_text(master, "", "真爱粉server启动成功...")

    # 设置信号被杀的回调
    def handler(sig, frame):
        # 退出前清理环境
        base_client.send_text(master, "", "真爱粉server正在关闭...")
        exit(0)

    signal.signal(signal.SIGINT, handler)


def main():
    # 初始化数据库
    create_db_and_table()
    # notice master
    notice_master()
    # 注册并且 异步启动定时任务
    job = Job()
    job.async_enable_jobs()
    # 启动http 这个留到最后启动 保活进程
    server.enable_http()


if __name__ == '__main__':
    main()
