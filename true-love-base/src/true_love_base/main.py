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


def disable_quick_edit():
    """
    禁用 Windows 控制台的 QuickEdit 模式
    
    QuickEdit 模式会导致用户点击控制台窗口时程序暂停，
    直到按回车键才会继续执行，这会影响消息监听的稳定性。
    """
    if sys.platform != 'win32':
        return

    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # 获取标准输入句柄 (STD_INPUT_HANDLE = -10)
        handle = kernel32.GetStdHandle(-10)
        # 获取当前控制台模式
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        # 禁用 QuickEdit 模式 (0x0040) 和插入模式 (0x0020)
        # ENABLE_QUICK_EDIT_MODE = 0x0040
        # ENABLE_INSERT_MODE = 0x0020
        new_mode = mode.value & ~0x0040 & ~0x0020
        kernel32.SetConsoleMode(handle, new_mode)
        LOG.info("Disabled Windows console QuickEdit mode")
    except Exception as e:
        # 非 Windows 环境或没有控制台时忽略
        LOG.debug(f"Could not disable QuickEdit mode: {e}")


def main():
    """主函数"""
    # 禁用 Windows 控制台 QuickEdit 模式，防止点击窗口导致程序暂停
    disable_quick_edit()

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
        # 清理 Robot 资源（线程池等）
        robot.cleanup()
        # 清理 wxauto 客户端资源
        client.cleanup()
        LOG.info("Cleanup completed, exiting...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 启动 HTTP 服务
    t = server.enable_http(robot)
    LOG.info("HTTP server enabled")

    # 发送启动通知
    try:
        robot.send_text_msg("True Love Base started successfully!", config.master_wix)
    except Exception as e:
        LOG.warning(f"Failed to send startup notification: {e}")

    LOG.info("True Love Base is ready!")
    LOG.info("Use HTTP API to add chat listeners:")
    LOG.info("  POST /listen/add  {\"chat_name\": \"好友昵称或群名\"}")

    # 定义监听线程的入口函数
    # 重要：AddListenChat 和 KeepRunning 必须在同一个线程中调用
    def listener_thread_entry():
        # 在监听线程中加载监听列表
        robot.load_listen_chats()
        listen_count = len(robot.get_listen_chats())
        if listen_count > 0:
            LOG.info(f"Loaded {listen_count} listen chats from file")
        else:
            LOG.warning("No listen_chats found! Use API to add listeners")
        # 开始监听（阻塞）
        robot.start_listening()

    # 在后台线程启动消息监听
    listen_thread = Thread(
        target=listener_thread_entry,
        name="MessageListener",
        daemon=True,
    )
    listen_thread.start()

    # 把http现成拉到主线程保持运行
    t.join()


if __name__ == '__main__':
    main()
