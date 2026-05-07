# -*- coding: utf-8 -*-
"""Lark Base 客户端实现"""

import json
import logging
import time

import requests

from ._interface import BaseClient

LOG = logging.getLogger("LarkBaseClient")
_TIMEOUT = (2, 10)


class LarkBaseClient(BaseClient):

    def _post(self, label: str, url: str, payload: str) -> requests.Response:
        LOG.info("→ [%s] req:[%s]", label, payload[:500])
        start = time.time()
        res = requests.post(url, headers={"Content-Type": "application/json"},
                            data=payload, timeout=_TIMEOUT)
        cost = (time.time() - start) * 1000
        try:
            LOG.info("← [%s] cost:[%.0fms] code:[%s] res:[%s]", label, cost, res.status_code, res.json())
        except Exception:
            LOG.info("← [%s] cost:[%.0fms] code:[%s] res:[%s]", label, cost, res.status_code, res.text[:500])
        return res

    def send_text(self, receiver: str, at_user: str, content: str,
                  raise_on_error: bool = False) -> tuple[bool, str]:
        url = f"{self.host}/action/send"
        payload = json.dumps({
            "token": self.token,
            "receiver": receiver,
            "content": content,
            "at_user": at_user or "",
        }, ensure_ascii=False)
        try:
            self._post("send_text", url, payload).raise_for_status()
            return True, ""
        except Exception as e:
            LOG.error("✗ [send_text][lark] 失败: %s", e)
            if raise_on_error:
                raise
            return False, str(e)

    @staticmethod
    def _infer_file_type(ref: str) -> str:
        ext = ref.split("?")[0].rsplit(".", 1)[-1].lower() if "." in ref else ""
        if ext in {"jpg", "jpeg", "png", "gif", "webp", "bmp"}:
            return "image"
        if ext in {"mp4", "mov", "avi", "mkv"}:
            return "video"
        if ext in {"mp3", "ogg", "m4a", "wav", "aac"}:
            return "audio"
        return "file"

    def send_file(self, ref: str, receiver: str,
                  raise_on_error: bool = False) -> tuple[bool, str]:
        """Lark Base 支持直接传 URL，由 lark-agent-base 负责上传到 Lark。"""
        url = f"{self.host}/action/send-file"
        payload = json.dumps({
            "token": self.token,
            "receiver": receiver,
            "file_type": self._infer_file_type(ref),
            "resource": {"ref": ref, "source": "url" if ref.startswith("http") else "local"},
        }, ensure_ascii=False)
        try:
            self._post("send_file", url, payload).raise_for_status()
            return True, ""
        except Exception as e:
            LOG.error("✗ [send_file][lark] 失败: %s", e)
            if raise_on_error:
                raise
            return False, str(e)
