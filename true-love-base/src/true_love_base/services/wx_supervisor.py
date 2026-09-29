# -*- coding: utf-8 -*-
"""
WxSupervisor - 微信连接守护

base 的存活不依赖微信：微信没开时定期重试连接，连上后定期确认登录态，
掉线后丢弃旧实例并重新连接。每次连上都重新注册监听。
"""

import logging
from threading import Event
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from true_love_base.core import WxAutoClient

LOG = logging.getLogger("WxSupervisor")


class WxSupervisor:
    """
    微信连接守护

    在调用线程里阻塞运行（base 的主线程），直到收到停止信号。
    """

    def __init__(
        self,
        client: "WxAutoClient",
        on_online: Callable[[], None],
        stop_event: Event,
        *,
        reconnect_interval: float = 10.0,
        health_interval: float = 30.0,
        offline_threshold: int = 2,
    ) -> None:
        """
        Args:
            client: 微信客户端
            on_online: 每次连上微信后调用，负责注册监听
            stop_event: 停止信号
            reconnect_interval: 离线时重试连接的间隔（秒）
            health_interval: 在线时检查登录态的间隔（秒）
            offline_threshold: 连续多少次检查失败才判定掉线
        """
        self._client = client
        self._on_online = on_online
        self._stop_event = stop_event
        self._reconnect_interval = reconnect_interval
        self._health_interval = health_interval
        self._offline_threshold = offline_threshold
        self._failed_checks = 0

    def run(self) -> None:
        """守护微信连接，直到收到停止信号"""
        while not self._stop_event.is_set():
            delay = self._step()
            if self._stop_event.wait(delay):
                return

    def _step(self) -> float:
        """推进一步，返回下一步之前要等待的秒数"""
        if not self._client.is_connected():
            return self._connect()
        return self._check()

    def _connect(self) -> float:
        if not self._client.connect():
            return self._reconnect_interval
        self._failed_checks = 0
        try:
            self._on_online()
        except Exception:
            LOG.exception("Failed to start listening after connecting to WeChat; reconnecting")
            self._client.disconnect()
            return self._reconnect_interval
        return self._health_interval

    def _check(self) -> float:
        if self._client.check_online():
            self._failed_checks = 0
            return self._health_interval
        self._failed_checks += 1
        if self._failed_checks < self._offline_threshold:
            LOG.warning("WeChat online check failed (%s/%s)", self._failed_checks, self._offline_threshold)
            return self._health_interval
        LOG.error("WeChat went offline; waiting for it to come back")
        self._client.disconnect()
        return self._reconnect_interval
