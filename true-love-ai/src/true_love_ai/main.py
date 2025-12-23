#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
True Love AI 主入口
"""
import logging
import signal

import uvicorn

from true_love_ai.core.config import get_config
from true_love_ai.base_client import send_text
from true_love_ai.llm.llm_bootstrap import init_litellm

LOG = logging.getLogger(__name__)


def notice_master():
    """启动通知"""
    try:
        send_text("master", "", "真爱粉 AI 启动成功啦~ ✨")
    except Exception as e:
        LOG.warning(f"启动通知发送失败: {e}")


def setup_signal_handlers():
    """设置信号处理"""

    def handler(sig, frame):
        LOG.info("收到关闭信号，正在退出...")
        try:
            send_text("master", "", "真爱粉 AI 正在关闭...")
        except Exception:
            pass
        exit(0)

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


def main():
    """主入口"""
    # 加载配置（日志已在 config 模块初始化时配置）
    config = get_config()

    # 初始化 LiteLLM
    init_litellm()

    # 设置信号处理
    setup_signal_handlers()

    # 启动通知
    notice_master()

    LOG.info("=" * 50)
    LOG.info("真爱粉 AI 服务启动中...")
    LOG.info(f"版本: 0.2.0")
    LOG.info(f"默认服务商: {config.default_provider}")
    LOG.info("=" * 50)

    # 获取 HTTP 配置
    http_config = config.http
    if not http_config:
        LOG.error("HTTP 配置缺失，无法启动服务")
        return

    # 启动 FastAPI 服务
    uvicorn.run(
        "true_love_ai.api.app:app",
        host=http_config.host,
        port=http_config.port,
        reload=False,
        log_level="info",
        access_log=False  # 使用自定义日志中间件
    )


if __name__ == "__main__":
    main()
