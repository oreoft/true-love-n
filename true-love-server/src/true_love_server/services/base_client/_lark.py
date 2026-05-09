# -*- coding: utf-8 -*-
"""Lark Base 客户端实现"""

import json
import logging

from true_love_common.http.client import HttpResult, async_post

from ._interface import BaseClient, api_response_ok, trace_headers

LOG = logging.getLogger("LarkBaseClient")
_TIMEOUT = (10, 30)


class LarkBaseClient(BaseClient):

    async def _post(self, label: str, url: str, payload: str) -> HttpResult:
        return await async_post(
            url,
            headers=trace_headers({"Content-Type": "application/json"}),
            data=payload,
            timeout=_TIMEOUT,
        )

    async def send_text(self, receiver: str, at_user: str, content: str,
                        raise_on_error: bool = False) -> tuple[bool, str]:
        url = f"{self.host}/action/send"
        payload = json.dumps({
            "token": self.token,
            "receiver": receiver,
            "content": content,
            "at_user": at_user or "",
        }, ensure_ascii=False)
        try:
            return api_response_ok(await self._post("send_text", url, payload))
        except Exception as e:
            LOG.error("Lark send_text failed: %s", e)
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

    async def send_file(self, ref: str, receiver: str,
                        raise_on_error: bool = False) -> tuple[bool, str]:
        """Lark 出站文件只透传 AI 图床 URL，由 lark-agent-base 负责上传到 Lark。"""
        if not ref.startswith("http://") and not ref.startswith("https://"):
            return False, f"Lark 文件发送只支持 URL: {ref}"

        url = f"{self.host}/action/send-file"
        payload = json.dumps({
            "token": self.token,
            "receiver": receiver,
            "file_type": self._infer_file_type(ref),
            "url": ref,
        }, ensure_ascii=False)
        try:
            return api_response_ok(await self._post("send_file", url, payload))
        except Exception as e:
            LOG.error("Lark send_file failed: %s", e)
            if raise_on_error:
                raise
            return False, str(e)
