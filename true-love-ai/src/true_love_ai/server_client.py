#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base 服务客户端
与 true-love-base 服务通信
"""
import json
import logging
import time

import httpx

from true_love_ai.core.config import get_config

LOG = logging.getLogger(__name__)


def send_text(send_receiver: str, at_receiver: str, content: str) -> str:
    """
    发送文本消息到 Base 服务
    
    Args:
        send_receiver: 发送目标
        at_receiver: @目标
        content: 消息内容
        
    Returns:
        空字符串
    """
    config = get_config()
    host = config.base_server.host
    token = config.http.token[0] if config.http and config.http.token else ""

    payload = json.dumps({
        "token": token,
        "sendReceiver": send_receiver,
        "atReceiver": at_receiver,
        "content": content
    }, ensure_ascii=False)

    headers = {'Content-Type': 'application/json'}

    try:
        start_time = time.time()
        LOG.info(f"开始请求 base 推送内容, req: [{payload[:100]}...]")

        with httpx.Client() as client:
            res = client.post(
                host,
                headers=headers,
                content=payload,
                timeout=httpx.Timeout(connect=2.0, read=60.0, write=60.0, pool=60.0)
            )
            res.raise_for_status()

        LOG.info(f"请求成功, cost: [{(time.time() - start_time) * 1000:.0f}ms]")

    except Exception as e:
        LOG.warning(f"send_text 失败: {e}")

    return ""


async def send_text_async(send_receiver: str, at_receiver: str, content: str) -> str:
    """
    异步发送文本消息到 Base 服务
    """
    config = get_config()
    host = config.base_server.host
    token = config.http.token[0] if config.http and config.http.token else ""

    payload = {
        "token": token,
        "sendReceiver": send_receiver,
        "atReceiver": at_receiver,
        "content": content
    }

    try:
        start_time = time.time()
        LOG.info("开始异步请求 base 推送内容")

        async with httpx.AsyncClient() as client:
            res = await client.post(
                host,
                json=payload,
                timeout=httpx.Timeout(connect=2.0, read=60.0, write=60.0, pool=60.0)
            )
            res.raise_for_status()

        LOG.info(f"请求成功, cost: [{(time.time() - start_time) * 1000:.0f}ms]")

    except Exception as e:
        LOG.warning(f"send_text_async 失败: {e}")

    return ""
