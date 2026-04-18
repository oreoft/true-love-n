# -*- coding: utf-8 -*-
"""
Server Callback Client

AI Agent 执行完后，通过这个客户端调用 Server 的 /action/* 接口
来完成 WeChat 操作（发消息、管理提醒、管理监听等）。
"""

import json
import logging
import time

import httpx

from true_love_ai.core.config import get_config

LOG = logging.getLogger("ServerClient")


def _get_server_url() -> str:
    return get_config().base_server.host.rstrip("/")


def _get_token() -> str:
    config = get_config()
    return config.http.token[0] if config.http and config.http.token else ""


def _trace_headers() -> dict:
    from true_love_ai.core.trace import get_trace_id
    return {"X-Trace-ID": get_trace_id()}


def _post(path: str, payload: dict, timeout: float = 10.0) -> dict:
    """同步 POST"""
    url = f"{_get_server_url()}{path}"
    payload["token"] = _get_token()
    req_str = json.dumps(payload, ensure_ascii=False)
    LOG.info("→ [%s] req:[%s]", path, req_str[:500])
    try:
        start = time.time()
        with httpx.Client(timeout=timeout) as client:
            res = client.post(url, json=payload, headers=_trace_headers())
            res.raise_for_status()
        cost = (time.time() - start) * 1000
        LOG.info("← [%s] cost:[%.0fms] code:[%s] res:[%s]", path, cost, res.status_code, res.text[:500])
        return res.json()
    except Exception as e:
        LOG.error("✗ [%s] 失败: %s", path, e)
        return {"code": -1, "msg": str(e)}


async def _async_post(path: str, payload: dict, timeout: float = 10.0) -> dict:
    """异步 POST"""
    url = f"{_get_server_url()}{path}"
    payload["token"] = _get_token()
    req_str = json.dumps(payload, ensure_ascii=False)
    LOG.info("→ [%s] req:[%s]", path, req_str[:500])
    try:
        start = time.time()
        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.post(url, json=payload, headers=_trace_headers())
            res.raise_for_status()
        cost = (time.time() - start) * 1000
        LOG.info("← [%s] cost:[%.0fms] code:[%s] res:[%s]", path, cost, res.status_code, res.text[:500])
        return res.json()
    except Exception as e:
        LOG.error("✗ [%s] 失败: %s", path, e)
        return {"code": -1, "msg": str(e)}


# ==================== 消息发送 ====================

def send_text_sync(receiver: str, content: str, at_user: str = "") -> bool:
    """同步发送文本消息（用于启动/关闭通知等非异步场景）"""
    result = _post("/action/send", {"receiver": receiver, "content": content, "at_user": at_user})
    return result.get("code") == 0


async def send_text(receiver: str, content: str, at_user: str = "") -> bool:
    result = await _async_post("/action/send", {
        "receiver": receiver, "content": content, "at_user": at_user,
    })
    return result.get("code") == 0


async def send_file(receiver: str, file_id: str, file_type: str = "image") -> bool:
    result = await _async_post("/action/send-file", {
        "receiver": receiver, "file_id": file_id, "file_type": file_type,
    })
    return result.get("code") == 0


# ==================== 提醒管理 ====================

async def add_reminder(job_id: str, target_time_iso: str, receiver: str,
                       content: str, at_user: str = "") -> dict:
    return await _async_post("/action/reminder/add", {
        "job_id": job_id, "target_time_iso": target_time_iso,
        "receiver": receiver, "at_user": at_user, "content": content,
    })


async def delete_reminder(job_id: str) -> bool:
    result = await _async_post("/action/reminder/delete", {"job_id": job_id})
    return result.get("code") == 0


async def query_reminders(receiver: str) -> list[dict]:
    result = await _async_post("/action/reminder/query", {"receiver": receiver})
    return result.get("data", {}).get("jobs", [])


# ==================== 监听管理 ====================

async def listen_add(chat_name: str) -> dict:
    return await _async_post("/action/listen/add", {"chat_name": chat_name})


async def listen_remove(chat_name: str) -> dict:
    return await _async_post("/action/listen/remove", {"chat_name": chat_name})


# ==================== 历史记录查询 ====================

async def query_history(chat_id: str, sender: str, limit: int = 100) -> list[dict]:
    result = await _async_post("/query/history", {
        "chat_id": chat_id, "sender": sender, "limit": limit,
    }, timeout=15.0)
    return result.get("data", {}).get("messages", [])
