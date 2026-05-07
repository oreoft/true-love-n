# -*- coding: utf-8 -*-
"""BaseClient 抽象接口 + 公共工具"""

import logging
import tempfile
from abc import ABC, abstractmethod

import requests

LOG = logging.getLogger("BaseClient")


class BaseClient(ABC):
    """Base 服务客户端抽象接口，每个平台提供独立实现。"""

    def __init__(self, host: str, token: str = ""):
        self.host = host.rstrip("/")
        self.token = token

    @abstractmethod
    def send_text(self, receiver: str, at_user: str, content: str,
                  raise_on_error: bool = False) -> tuple[bool, str]:
        """发送文本消息。"""

    @abstractmethod
    def send_file(self, ref: str, receiver: str,
                  raise_on_error: bool = False) -> tuple[bool, str]:
        """
        发送文件。

        ref: HTTP URL 或本地路径，各实现自行决定如何处理。
        文件类型由 ref 扩展名推断，无需调用方传入。
        """


def download_to_tmp(url: str) -> str:
    """从 URL 下载文件到临时目录，返回临时文件路径。后缀从 URL 路径推断。"""
    url_path = url.split("?")[0]
    if "." in url_path.rsplit("/", 1)[-1]:
        suffix = "." + url_path.rsplit(".", 1)[-1].lower()
    else:
        suffix = ".bin"

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    LOG.info("→ 下载资源: %s", url)
    resp = requests.get(url, timeout=(10, 60))
    resp.raise_for_status()
    tmp.write(resp.content)
    tmp.close()
    LOG.info("← 写入临时文件: %s (%d bytes)", tmp.name, len(resp.content))
    return tmp.name
