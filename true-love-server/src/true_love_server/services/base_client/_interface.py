# -*- coding: utf-8 -*-
"""BaseClient 抽象接口 + 公共工具"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

LOG = logging.getLogger("BaseClient")


def api_response_ok(res: requests.Response) -> tuple[bool, str]:
    """检查 HTTP 和业务响应码。HTTP 200 但 code != 0 也算失败。"""
    res.raise_for_status()
    try:
        data = res.json()
    except Exception:
        return True, ""

    if isinstance(data, dict):
        code = data.get("code", 0)
        if str(code) != "0":
            return False, data.get("message") or data.get("msg") or str(data)
        if data.get("success") is False:
            return False, data.get("message") or data.get("msg") or str(data)
    return True, ""


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


_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
_VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv"}


def _download_dir_for(suffix: str) -> Path:
    if suffix in _IMAGE_EXTS:
        return Path("gen-img")
    if suffix in _VIDEO_EXTS:
        return Path("gen-video")
    return Path("files-save")


def download_to_tmp(url: str) -> str:
    """从 URL 下载到 Base/Server 共享目录，返回 Base 可解析的相对路径。"""
    url_path = unquote(urlparse(url).path)
    filename = Path(url_path).name or "download.bin"
    suffix = Path(filename).suffix.lower() or ".bin"
    save_dir = _download_dir_for(suffix)
    save_dir.mkdir(parents=True, exist_ok=True)

    file_path = save_dir / filename
    LOG.info("→ 下载资源: %s", url)
    resp = requests.get(url, timeout=(10, 60))
    resp.raise_for_status()
    file_path.write_bytes(resp.content)
    rel_path = file_path.as_posix()
    LOG.info("← 写入共享文件: %s (%d bytes)", rel_path, len(resp.content))
    return rel_path
