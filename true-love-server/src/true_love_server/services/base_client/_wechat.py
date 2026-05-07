# -*- coding: utf-8 -*-
"""WeChat Base 客户端实现"""

import json
import logging
import os
import time

import requests

from ._interface import BaseClient, download_to_tmp

LOG = logging.getLogger("WeChatBaseClient")
_TIMEOUT = (2, 10)


class WeChatBaseClient(BaseClient):

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

    # ==================== 通用接口实现 ====================

    def send_text(self, receiver: str, at_user: str, content: str,
                  raise_on_error: bool = False) -> tuple[bool, str]:
        url = f"{self.host}/send/text"
        payload = json.dumps({"sendReceiver": receiver, "atReceiver": at_user, "content": content},
                             ensure_ascii=False)
        try:
            self._post("send_text", url, payload).raise_for_status()
            return True, ""
        except Exception as e:
            LOG.error("✗ [send_text][wechat] 失败: %s", e)
            if raise_on_error:
                raise
            return False, str(e)

    def send_file(self, ref: str, receiver: str,
                  raise_on_error: bool = False) -> tuple[bool, str]:
        """ref 为 URL 时先下载到临时文件，为本地路径时直接发送。"""
        is_url = ref.startswith("http://") or ref.startswith("https://")
        tmp_path = None
        try:
            actual_path = download_to_tmp(ref) if is_url else ref
            if is_url:
                tmp_path = actual_path

            url = f"{self.host}/send/file"
            payload = json.dumps({"path": actual_path, "sendReceiver": receiver}, ensure_ascii=False)
            self._post("send_file", url, payload).raise_for_status()
            return True, ""
        except Exception as e:
            LOG.error("✗ [send_file][wechat] 失败: %s", e)
            if raise_on_error:
                raise
            return False, str(e)
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    # ==================== WeChat 专属操作 ====================

    def send_img(self, path: str, receiver: str, raise_on_error: bool = False) -> tuple[bool, str]:
        return self.send_file(path, receiver, raise_on_error=raise_on_error)

    def send_video(self, path: str, receiver: str, raise_on_error: bool = False) -> tuple[bool, str]:
        return self.send_file(path, receiver, raise_on_error=raise_on_error)

    def get_by_room_id(self, room_id) -> dict:
        payload = json.dumps({"room_id": room_id}, ensure_ascii=False)
        try:
            res = self._post("get_by_room_id", f"{self.host}/get/by/room-id", payload)
            res.raise_for_status()
            return res.json()["data"]
        except Exception as e:
            LOG.error("✗ [get_by_room_id] 失败: %s", e)
        return {}

    def add_listen_chat(self, nickname: str) -> dict:
        payload = json.dumps({"nickname": nickname}, ensure_ascii=False)
        try:
            res = self._post("add_listen_chat", f"{self.host}/listen/add", payload)
            res.raise_for_status()
            result = res.json()
            return {"success": result.get("code") == 0, "data": result.get("data"), "message": result.get("msg", "")}
        except Exception as e:
            LOG.error("✗ [add_listen_chat] 失败: %s", e)
            return {"success": False, "data": None, "message": str(e)}

    def execute_wx(self, method_name: str, params: dict = None) -> dict:
        payload = json.dumps({"name": method_name, "params": params or {}}, ensure_ascii=False)
        try:
            res = self._post("execute_wx", f"{self.host}/execute/wx", payload)
            res.raise_for_status()
            result = res.json()
            return {"success": result.get("code") == 0, "data": result.get("data"), "message": result.get("msg", "")}
        except Exception as e:
            LOG.error("✗ [execute_wx] 失败: %s", e)
            return {"success": False, "data": None, "message": str(e)}

    def execute_chat(self, chat_name: str, method_name: str, params: dict = None) -> dict:
        payload = json.dumps({"chat_name": chat_name, "name": method_name, "params": params or {}},
                             ensure_ascii=False)
        try:
            res = self._post("execute_chat", f"{self.host}/execute/chat", payload)
            res.raise_for_status()
            result = res.json()
            return {"success": result.get("code") == 0, "data": result.get("data"), "message": result.get("msg", "")}
        except Exception as e:
            LOG.error("✗ [execute_chat] 失败: %s", e)
            return {"success": False, "data": None, "message": str(e)}

    def batch_chat_info(self, chat_names: list[str]) -> dict:
        if not chat_names:
            return {"success": True, "data": {"results": {}}, "message": ""}
        payload = json.dumps({"chat_names": chat_names}, ensure_ascii=False)
        try:
            res = self._post("batch_chat_info", f"{self.host}/execute/batch-chat-info", payload)
            res.raise_for_status()
            result = res.json()
            return {"success": result.get("code") == 0, "data": result.get("data"), "message": result.get("msg", "")}
        except Exception as e:
            LOG.error("✗ [batch_chat_info] 失败: %s", e)
            return {"success": False, "data": None, "message": str(e)}
