# -*- coding: utf-8 -*-
"""
Server Client - 与后端 AI 服务通信

负责将消息发送到后端服务处理，并返回回复。
使用 Session 复用 HTTP 连接，线程安全的熔断器。
"""

import logging
import threading
import time
from typing import Optional

import requests

from true_love_base.configuration import Config
from true_love_base.models.api import ChatRequest, ChatResponse
from true_love_base.models.message import ChatMessage

config = Config()
LOG = logging.getLogger("ServerClient")

# 服务端配置
SERVER_HOST = "http://localhost:8088"
CHAT_ENDPOINT = f"{SERVER_HOST}/get-chat"


# ==================== HTTP Session 连接复用 ====================

_session: Optional[requests.Session] = None
_session_lock = threading.Lock()


def _get_session() -> requests.Session:
    """
    获取全局 HTTP Session（线程安全）
    
    复用 TCP 连接，减少握手开销。
    """
    global _session
    if _session is None:
        with _session_lock:
            if _session is None:
                _session = requests.Session()
                _session.headers.update({"Content-Type": "application/json"})
                LOG.info("HTTP Session created for connection reuse")
    return _session


# ==================== 线程安全的熔断器 ====================

class CircuitBreaker:
    """
    线程安全的熔断器
    
    当连续失败次数超过阈值时，熔断器打开，
    在重置超时后自动尝试恢复。
    """
    
    def __init__(self, threshold: int = 3, reset_timeout: int = 60):
        """
        初始化熔断器
        
        Args:
            threshold: 失败阈值，超过后熔断器打开
            reset_timeout: 重置超时时间（秒）
        """
        self._lock = threading.Lock()
        self._fail_count = 0
        self._last_fail_time = 0.0
        self._threshold = threshold
        self._reset_timeout = reset_timeout
    
    def record_failure(self) -> None:
        """记录一次失败"""
        with self._lock:
            self._fail_count += 1
            self._last_fail_time = time.time()
            LOG.warning(f"Circuit breaker: failure recorded, count={self._fail_count}")
    
    def record_success(self) -> None:
        """记录一次成功，重置失败计数"""
        with self._lock:
            if self._fail_count > 0:
                LOG.info("Circuit breaker: success recorded, resetting")
            self._fail_count = 0
            self._last_fail_time = 0.0
    
    def is_open(self) -> bool:
        """
        检查熔断器是否打开
        
        Returns:
            True 表示熔断器打开（应该拒绝请求）
        """
        with self._lock:
            if self._fail_count < self._threshold:
                return False
            
            # 检查是否超过重置时间
            if time.time() - self._last_fail_time >= self._reset_timeout:
                LOG.info("Circuit breaker: reset timeout reached, allowing retry")
                self._fail_count = 0
                self._last_fail_time = 0.0
                return False
            
            return True
    
    @property
    def fail_count(self) -> int:
        """获取当前失败次数"""
        with self._lock:
            return self._fail_count


# 全局熔断器实例
_circuit_breaker = CircuitBreaker(threshold=3, reset_timeout=60)


# ==================== API 函数 ====================

def get_chat(msg: ChatMessage) -> str:
    """
    发送消息到服务端获取回复
    
    Args:
        msg: 消息对象
        
    Returns:
        服务端返回的回复内容
    """
    # 检查熔断器
    if _circuit_breaker.is_open():
        LOG.warning("Circuit breaker is open, request rejected")
        return _get_error_message()
    
    try:
        # 构建请求
        request = ChatRequest(token=config.http_token, message=msg)
        payload = request.to_json()
        
        LOG.info(f"Sending to server: {payload[:2000]}...")
        
        # 使用 Session 发起请求（连接复用）
        session = _get_session()
        start_time = time.time()
        response = session.post(
            CHAT_ENDPOINT,
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
            _circuit_breaker.record_success()
            return chat_response.data or ""
        else:
            LOG.error(f"Server returned error: {resp_data}")
            return _get_error_message()
            
    except requests.exceptions.Timeout:
        LOG.error("Request timeout")
        _circuit_breaker.record_failure()
        return _get_error_message()
        
    except requests.exceptions.RequestException as e:
        LOG.error(f"Request failed: {e}")
        _circuit_breaker.record_failure()
        return _get_error_message()
        
    except Exception as e:
        LOG.error(f"Unexpected error: {e}")
        _circuit_breaker.record_failure()
        return _get_error_message()


def _get_error_message() -> str:
    """获取错误提示消息"""
    if _circuit_breaker.fail_count < 3:
        return "啊哦~，可能内容太长搬运超时，再试试捏"
    return "啊哦~, 服务正在重新调整，请稍后重试再试"
