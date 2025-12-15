# -*- coding: utf-8 -*-
"""
Server Client - 与后端 AI 服务通信

负责将消息发送到后端服务处理，并返回回复。
"""

import logging
import time
from typing import Optional

import requests

from configuration import Config
from models.message import BaseMessage
from models.api import ChatRequest, ChatResponse

config = Config()
LOG = logging.getLogger("ServerClient")

# 服务端配置
SERVER_HOST = "http://localhost:8088"
CHAT_ENDPOINT = f"{SERVER_HOST}/get-chat"

# 熔断器配置
CIRCUIT_BREAKER = {
    "fail_count": 0,
    "last_fail_time": 0,
    "threshold": 3,  # 失败阈值
    "reset_timeout": 60,  # 重置超时（秒）
}


def _reset_circuit_breaker():
    """重置熔断器状态"""
    CIRCUIT_BREAKER["fail_count"] = 0
    CIRCUIT_BREAKER["last_fail_time"] = 0


def _record_failure():
    """记录失败"""
    CIRCUIT_BREAKER["fail_count"] += 1
    CIRCUIT_BREAKER["last_fail_time"] = int(time.time())


def _is_circuit_open() -> bool:
    """检查熔断器是否打开"""
    if CIRCUIT_BREAKER["fail_count"] < CIRCUIT_BREAKER["threshold"]:
        return False
    
    # 检查是否超过重置时间
    current_time = int(time.time())
    if current_time - CIRCUIT_BREAKER["last_fail_time"] >= CIRCUIT_BREAKER["reset_timeout"]:
        _reset_circuit_breaker()
        return False
    
    return True


def get_chat(msg: BaseMessage) -> str:
    """
    发送消息到服务端获取回复
    
    Args:
        msg: 消息对象
        
    Returns:
        服务端返回的回复内容
    """
    try:
        # 构建请求
        request = ChatRequest.from_message(msg, config.http_token)
        payload = request.to_json()
        
        LOG.info(f"Sending to server: {payload[:200]}...")
        
        # 发起请求
        start_time = time.time()
        response = requests.post(
            CHAT_ENDPOINT,
            headers={"Content-Type": "application/json"},
            data=payload,
            timeout=(2, 60),  # 连接超时2秒，读取超时60秒
        )
        
        cost_ms = (time.time() - start_time) * 1000
        LOG.info(f"Server response received, cost: {cost_ms:.0f}ms")
        
        # 检查 HTTP 状态
        response.raise_for_status()
        
        # 解析响应
        resp_data = response.json()
        chat_response = ChatResponse.from_dict(resp_data)
        
        if chat_response.is_success:
            _reset_circuit_breaker()
            return chat_response.data or ""
        else:
            LOG.error(f"Server returned error: {resp_data}")
            return _get_error_message()
            
    except requests.exceptions.Timeout:
        LOG.error("Request timeout")
        _record_failure()
        return _get_error_message()
        
    except requests.exceptions.RequestException as e:
        LOG.error(f"Request failed: {e}")
        _record_failure()
        return _get_error_message()
        
    except Exception as e:
        LOG.error(f"Unexpected error: {e}")
        _record_failure()
        return _get_error_message()


def _get_error_message() -> str:
    """获取错误提示消息"""
    if CIRCUIT_BREAKER["fail_count"] < CIRCUIT_BREAKER["threshold"]:
        return "Oops! Request timeout, please try again~"
    return "Oops! Service is adjusting, please try again later~"
