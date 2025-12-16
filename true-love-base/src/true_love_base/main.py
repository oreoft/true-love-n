# -*- coding: utf-8 -*-
"""
True Love Base - Main Entry Point

微信消息处理服务的主入口。
基于 wxautox4 实现微信自动化。
"""

import logging
import signal
import sys
import time
from threading import Thread

from true_love_base.configuration import Config
from true_love_base.adapters import WxAutoClient
from true_love_base.services.robot import Robot
from true_love_base.services.listen_store import ListenStore
from true_love_base import server

# 初始化配置（会设置日志）
config = Config()
LOG = logging.getLogger("Main")


def main():
    """主函数"""
    LOG.info("=" * 50)
    LOG.info("True Love Base starting...")
    LOG.info("=" * 50)
    
    # 初始化微信客户端
    try:
        client = WxAutoClient()
        LOG.info(f"WeChat client initialized, self: {client.get_self_name()}")
    except Exception as e:
        LOG.error(f"Failed to initialize WeChat client: {e}")
        sys.exit(1)
    
    # 初始化监听列表持久化管理器
    listen_store = ListenStore(config.listen_chats_file)
    LOG.info(f"ListenStore initialized: {config.listen_chats_file}")
    
    # 初始化机器人
    robot = Robot(client, listen_store)
    
    # 设置信号处理
    def signal_handler(sig, frame):
        LOG.info("Received shutdown signal...")
        try:
            robot.send_text_msg("True Love Base shutting down...", config.master_wix)
        except Exception:
            pass
        client.cleanup()
        LOG.info("Cleanup completed, exiting...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动 HTTP 服务
    server.enable_http(robot)
    LOG.info("HTTP server enabled")
    
    # 发送启动通知
    try:
        robot.send_text_msg("True Love Base started successfully!", config.master_wix)
    except Exception as e:
        LOG.warning(f"Failed to send startup notification: {e}")
    
    # 从持久化文件加载监听列表
    robot.load_listen_chats()
    listen_count = len(robot.get_listen_chats())
    if listen_count > 0:
        LOG.info(f"Loaded {listen_count} listen chats from file")
    else:
        LOG.warning("No listen_chats found! Use API to add listeners")
    
    LOG.info("True Love Base is ready!")
    LOG.info("Use HTTP API to add chat listeners:")
    LOG.info("  POST /listen/add  {\"chat_name\": \"好友昵称或群名\"}")
    
    # 在后台线程启动消息监听
    listen_thread = Thread(
        target=robot.start_listening,
        name="MessageListener",
        daemon=True,
    )
    listen_thread.start()
    
    # 主线程保持运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == '__main__':
    main()
