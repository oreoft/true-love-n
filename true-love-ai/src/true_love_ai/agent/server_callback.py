# -*- coding: utf-8 -*-
"""
Server Callback Client

AI Agent 执行完 skill 后，通过这个客户端调用 Server 的 /action/* 接口
来完成 WeChat 操作（发消息、管理提醒、管理监听等）。
"""

import json
import logging
import time

import httpx

from true_love_ai.core.config import get_config

LOG = logging.getLogger("ServerCallback")


def _get_server_url() -> str:
    config = get_config()
    return config.base_server.host.rstrip("/")


def _get_token() -> str:
    config = get_config()
    return config.http.token[0] if config.http and config.http.token else ""


def _post(path: str, payload: dict, timeout: float = 10.0) -> dict:
    """同步 POST 到 Server /action/* 接口"""
    url = f"{_get_server_url()}{path}"
    payload["token"] = _get_token()
    try:
        start = time.time()
        with httpx.Client(timeout=timeout) as client:
            res = client.post(url, json=payload)
            res.raise_for_status()
        LOG.info("%s cost=%.0fms", path, (time.time() - start) * 1000)
        return res.json()
    except Exception as e:
        LOG.error("Server callback %s 失败: %s", path, e)
        return {"code": -1, "msg": str(e)}


async def _async_post(path: str, payload: dict, timeout: float = 10.0) -> dict:
    """异步 POST 到 Server /action/* 接口"""
    url = f"{_get_server_url()}{path}"
    payload["token"] = _get_token()
    try:
        start = time.time()
        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.post(url, json=payload)
            res.raise_for_status()
        LOG.info("%s cost=%.0fms", path, (time.time() - start) * 1000)
        return res.json()
    except Exception as e:
        LOG.error("Server callback %s 失败: %s", path, e)
        return {"code": -1, "msg": str(e)}


# ==================== 消息发送 ====================

async def send_text(receiver: str, content: str, at_user: str = "") -> bool:
    """发送文本消息"""
    result = await _async_post("/action/send", {
        "receiver": receiver,
        "content": content,
        "at_user": at_user,
    })
    return result.get("code") == 0


async def send_file(receiver: str, path: str, file_type: str = "image") -> bool:
    """发送文件/图片/视频"""
    result = await _async_post("/action/send-file", {
        "receiver": receiver,
        "path": path,
        "file_type": file_type,
    })
    return result.get("code") == 0


# ==================== 提醒管理 ====================

async def add_reminder(job_id: str, target_time_iso: str, receiver: str,
                       content: str, at_user: str = "") -> dict:
    """添加定时提醒"""
    return await _async_post("/action/reminder/add", {
        "job_id": job_id,
        "target_time_iso": target_time_iso,
        "receiver": receiver,
        "at_user": at_user,
        "content": content,
    })


async def delete_reminder(job_id: str) -> bool:
    """删除定时提醒"""
    result = await _async_post("/action/reminder/delete", {"job_id": job_id})
    return result.get("code") == 0


async def query_reminders(receiver: str) -> list[dict]:
    """查询提醒列表"""
    result = await _async_post("/action/reminder/query", {"receiver": receiver})
    return result.get("data", {}).get("jobs", [])


# ==================== 监听管理 ====================

async def listen_add(chat_name: str) -> dict:
    """添加监听"""
    return await _async_post("/action/listen/add", {"chat_name": chat_name})


async def listen_remove(chat_name: str) -> dict:
    """移除监听"""
    return await _async_post("/action/listen/remove", {"chat_name": chat_name})


# ==================== 历史记录查询 ====================

async def query_history(chat_id: str, sender: str, limit: int = 100) -> list[dict]:
    """从 Server 查询群消息历史（用于 analyze_speech）"""
    url = f"{_get_server_url()}/query/history"
    payload = {
        "token": _get_token(),
        "chat_id": chat_id,
        "sender": sender,
        "limit": limit,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, json=payload)
            res.raise_for_status()
            data = res.json()
            return data.get("data", {}).get("messages", [])
    except Exception as e:
        LOG.error("query_history 失败: %s", e)
        return []
