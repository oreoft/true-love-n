# -*- coding: utf-8 -*-
"""
Base Client - 基础通信客户端

与 base 服务通信，发送消息、图片等。
"""

import json
import logging
import time

import requests

from ..core import Config

config = Config()
host = config.BASE_SERVER["host"]
text_url = f"{host}/send/text"
text_file = f"{host}/send/file"
get_by_room_id_url = f"{host}/get/by/room-id"
add_listen_url = f"{host}/listen/add"
execute_wx_url = f"{host}/execute/wx"
execute_chat_url = f"{host}/execute/chat"
batch_chat_info_url = f"{host}/execute/batch-chat-info"
LOG = logging.getLogger("BaseClient")
time_out = (2, 10)


def _do_post(label: str, url: str, payload: str) -> requests.Response:
    LOG.info("→ [%s] req:[%s]", label, payload[:500])
    start = time.time()
    res = requests.post(url, headers={"Content-Type": "application/json"}, data=payload, timeout=time_out)
    cost = (time.time() - start) * 1000
    try:
        LOG.info("← [%s] cost:[%.0fms] code:[%s] res:[%s]", label, cost, res.status_code, res.json())
    except Exception:
        LOG.info("← [%s] cost:[%.0fms] code:[%s] res:[%s]", label, cost, res.status_code, res.text[:500])
    return res


def send_text(send_receiver, at_receiver, content, raise_on_error: bool = False) -> tuple[bool, str]:
    payload = json.dumps({
        "sendReceiver": send_receiver,
        "atReceiver": at_receiver,
        "content": content,
    }, ensure_ascii=False)
    try:
        res = _do_post("send_text", text_url, payload)
        res.raise_for_status()
        return True, ""
    except Exception as e:
        LOG.error("✗ [send_text] 失败: %s", e)
        if raise_on_error:
            raise
        return False, str(e)


def send_img(path, send_receiver, raise_on_error: bool = False) -> tuple[bool, str]:
    payload = json.dumps({"path": path, "sendReceiver": send_receiver}, ensure_ascii=False)
    try:
        res = _do_post("send_img", text_file, payload)
        res.raise_for_status()
        return True, ""
    except Exception as e:
        LOG.error("✗ [send_img] 失败: %s", e)
        if raise_on_error:
            raise
        return False, str(e)


def send_video(path, send_receiver, raise_on_error: bool = False) -> tuple[bool, str]:
    payload = json.dumps({"path": path, "sendReceiver": send_receiver}, ensure_ascii=False)
    try:
        res = _do_post("send_video", text_file, payload)
        res.raise_for_status()
        return True, ""
    except Exception as e:
        LOG.error("✗ [send_video] 失败: %s", e)
        if raise_on_error:
            raise
        return False, str(e)


def get_by_room_id(room_id) -> dict:
    payload = json.dumps({"room_id": room_id}, ensure_ascii=False)
    try:
        res = _do_post("get_by_room_id", get_by_room_id_url, payload)
        res.raise_for_status()
        return res.json()["data"]
    except Exception as e:
        LOG.error("✗ [get_by_room_id] 失败: %s", e)
    return {}


def add_listen_chat(nickname: str) -> dict:
    payload = json.dumps({"nickname": nickname}, ensure_ascii=False)
    try:
        res = _do_post("add_listen_chat", add_listen_url, payload)
        res.raise_for_status()
        result = res.json()
        return {"success": result.get("code") == 0, "data": result.get("data"), "message": result.get("msg", "")}
    except Exception as e:
        LOG.error("✗ [add_listen_chat] 失败: %s", e)
        return {"success": False, "data": None, "message": str(e)}


def execute_wx(method_name: str, params: dict = None) -> dict:
    payload = json.dumps({"name": method_name, "params": params or {}}, ensure_ascii=False)
    try:
        res = _do_post("execute_wx", execute_wx_url, payload)
        res.raise_for_status()
        result = res.json()
        return {"success": result.get("code") == 0, "data": result.get("data"), "message": result.get("msg", "")}
    except Exception as e:
        LOG.error("✗ [execute_wx] 失败: %s", e)
        return {"success": False, "data": None, "message": str(e)}


def execute_chat(chat_name: str, method_name: str, params: dict = None) -> dict:
    payload = json.dumps({"chat_name": chat_name, "name": method_name, "params": params or {}}, ensure_ascii=False)
    try:
        res = _do_post("execute_chat", execute_chat_url, payload)
        res.raise_for_status()
        result = res.json()
        return {"success": result.get("code") == 0, "data": result.get("data"), "message": result.get("msg", "")}
    except Exception as e:
        LOG.error("✗ [execute_chat] 失败: %s", e)
        return {"success": False, "data": None, "message": str(e)}


def batch_chat_info(chat_names: list[str]) -> dict:
    if not chat_names:
        return {"success": True, "data": {"results": {}}, "message": ""}
    payload = json.dumps({"chat_names": chat_names}, ensure_ascii=False)
    try:
        res = _do_post("batch_chat_info", batch_chat_info_url, payload)
        res.raise_for_status()
        result = res.json()
        return {"success": result.get("code") == 0, "data": result.get("data"), "message": result.get("msg", "")}
    except Exception as e:
        LOG.error("✗ [batch_chat_info] 失败: %s", e)
        return {"success": False, "data": None, "message": str(e)}
