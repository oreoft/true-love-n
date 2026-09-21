# -*- coding: utf-8 -*-
"""
True Love Base - Main Entry Point

微信消息处理服务的主入口。
基于 wxautox4 实现微信自动化。
"""

import logging
import signal
import sys
from threading import Event

from true_love_base.api import server
from true_love_base.configuration import Config
from true_love_base.core import WxAutoClient
from true_love_base.services.listen_store import ListenStore
from true_love_base.services.robot import Robot

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

    # 初始化微信客户端和机器人
    client, robot = init_wx()

    # 关闭事件，用于优雅退出
    shutdown_event = Event()

    # 设置信号处理
    def signal_handler(sig, frame):
        LOG.info("Received shutdown signal %s, shutting down...", sig)
        shutdown_event.set()  # 通知主线程退出

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Callbacks can trigger replies while the saved listeners are still loading.
        server.enable_http(robot)
        LOG.info("HTTP server enabled")
        # AddListenChat starts SDK listening; this main loop keeps the process alive.
        init_listening(robot, shutdown_event)
        if shutdown_event.is_set():
            return

        LOG.info("True Love Base is ready!")
        LOG.info("Use HTTP API to add chat listeners:")
        LOG.info("  POST /listen/add  {\"chat_name\": \"好友昵称或群名\"}")

        while not shutdown_event.wait(timeout=0.2):
            pass

        try:
            if not robot.send_text_msg("True Love Base shutting down...", config.master_wix):
                LOG.warning("Shutdown notification was not delivered to [%s]", config.master_wix)
        except Exception:
            LOG.warning("Failed to send shutdown notification to [%s]", config.master_wix, exc_info=True)
    except Exception:
        LOG.exception("Base runtime failed; shutting down")
        raise
    finally:
        LOG.info("Cleaning up...")
        try:
            client.cleanup()
        finally:
            robot.cleanup()
        LOG.info("Cleanup completed, bye!")


def init_listening(robot: Robot, stop_event: Event) -> None:
    """Register saved listeners once; the SDK owns its listener threads."""
    load_result = robot.load_listen_chats(stop_event=stop_event)
    if stop_event.is_set():
        return
    success_chats = load_result["success"]
    failed_chats = load_result["failed"]

    if len(success_chats) > 0:
        LOG.info(f"Loaded {len(success_chats)} listen chats from file")
    else:
        LOG.warning("No listen_chats found! Use API to add listeners")

    if len(failed_chats) > 0:
        LOG.warning(f"Failed to load {len(failed_chats)} listen chats: {failed_chats}")

    # 发送启动通知，包含监听成功和失败的列表
    try:
        success_list_str = "\n".join(
            [f"  {i + 1}. {name}" for i, name in enumerate(success_chats)]) if success_chats else "  (无)"
        failed_list_str = "\n".join(
            [f"  {i + 1}. {name}" for i, name in enumerate(failed_chats)]) if failed_chats else "  (无)"

        startup_msg = f"True Love Base started successfully!\n\n当前监听列表 ({len(success_chats)}个):\n{success_list_str}"
        if failed_chats:
            startup_msg += f"\n\n监听失败 ({len(failed_chats)}个):\n{failed_list_str}"

        if not robot.send_text_msg(startup_msg, config.master_wix):
            LOG.warning("Startup notification was not delivered to [%s]", config.master_wix)
    except Exception:
        LOG.warning("Failed to send startup notification to [%s]", config.master_wix, exc_info=True)


def init_wx() -> tuple[WxAutoClient, Robot]:
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
    return client, robot


if __name__ == '__main__':
    main()
