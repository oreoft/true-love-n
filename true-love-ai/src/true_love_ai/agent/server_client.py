# -*- coding: utf-8 -*-
"""
Server Callback Client

AI Agent 执行完后，通过这个客户端调用 Server 的 /action/* 接口
来完成 WeChat 操作（发消息、管理提醒、管理监听等）。
"""

import json
import logging

from true_love_common.http.client import async_get, async_post_json, post_json

from true_love_ai.core.config import get_config

LOG = logging.getLogger("ServerClient")


def _get_server_url() -> str:
    return get_config().base_server.host.rstrip("/")


def _get_token() -> str:
    config = get_config()
    return config.http.token[0] if config.http and config.http.token else ""


def _post(path: str, payload: dict, timeout: float = 10.0) -> dict:
    """同步 POST"""
    url = f"{_get_server_url()}{path}"
    payload["token"] = _get_token()
    req_str = json.dumps(payload, ensure_ascii=False)
    LOG.info("→ [%s] req:[%s]", path, req_str[:500])
    result = post_json(url, payload, timeout=timeout)
    LOG.info("← [%s] cost:[%.0fms] code:[%s] res:[%s]", path, result.cost_ms, result.status_code, result.text[:500])
    if result.ok:
        return result.data if isinstance(result.data, dict) else {}
    LOG.error("✗ [%s] 失败: %s", path, result.error or result.text)
    return {"code": -1, "msg": result.error or result.text}


async def _async_post(path: str, payload: dict, timeout: float = 10.0) -> dict:
    """异步 POST"""
    url = f"{_get_server_url()}{path}"
    payload["token"] = _get_token()
    req_str = json.dumps(payload, ensure_ascii=False)
    LOG.info("→ [%s] req:[%s]", path, req_str[:500])
    result = await async_post_json(url, payload, timeout=timeout)
    LOG.info("← [%s] cost:[%.0fms] code:[%s] res:[%s]", path, result.cost_ms, result.status_code, result.text[:500])
    if result.ok:
        return result.data if isinstance(result.data, dict) else {}
    LOG.error("✗ [%s] 失败: %s", path, result.error or result.text)
    return {"code": -1, "msg": result.error or result.text}


# ==================== 消息发送 ====================

def send_text_sync(receiver: str, content: str, at_user: str = "",
                   platform: str = "wechat") -> bool:
    """同步发送文本消息（用于启动/关闭通知等非异步场景）"""
    result = _post("/action/send", {
        "receiver": receiver, "content": content, "at_user": at_user, "platform": platform,
    })
    return result.get("code") == 0


async def send_text(receiver: str, content: str, at_user: str = "",
                    platform: str = "wechat") -> bool:
    result = await _async_post("/action/send", {
        "receiver": receiver, "content": content, "at_user": at_user, "platform": platform,
    })
    return result.get("code") == 0


async def send_file(receiver: str, path: str, platform: str = "wechat") -> bool:
    """
    通知 Server 发送 AI 生成的文件。

    path: AI 本地相对路径，如 gen_img/abc123.jpg、gen_video/abc123.mp4
          Server 会用自己配置的 ai_host 拼出完整 URL 再下载。
    """
    result = await _async_post("/action/send-file", {
        "receiver": receiver, "path": path, "platform": platform,
    })
    return result.get("code") == 0


# ==================== 提醒管理 ====================

async def add_reminder(job_id: str, target_time_iso: str, receiver: str,
                       content: str, at_user: str = "",
                       platform: str = "wechat") -> dict:
    return await _async_post("/action/reminder/add", {
        "job_id": job_id, "target_time_iso": target_time_iso,
        "receiver": receiver, "at_user": at_user, "content": content,
        "platform": platform,
    })


async def delete_reminder(job_id: str) -> bool:
    result = await _async_post("/action/reminder/delete", {"job_id": job_id})
    return result.get("code") == 0


async def query_reminders(receiver: str, platform: str = "wechat") -> list[dict]:
    result = await _async_post("/action/reminder/query", {
        "receiver": receiver,
        "platform": platform,
    })
    return result.get("data", {}).get("jobs", [])


# ==================== 监听管理 ====================

async def listen_add(chat_name: str) -> dict:
    return await _async_post("/action/listen/add", {"chat_name": chat_name})


async def listen_remove(chat_name: str) -> dict:
    return await _async_post("/action/listen/remove", {"chat_name": chat_name})


# ==================== 媒体文件获取 ====================

def _get_media_host(platform: str) -> str:
    cfg = get_config().base_server
    if platform == "lark":
        return cfg.lark_host.rstrip("/")
    return _get_server_url()


async def fetch_media_bytes(ref: str, platform: str = "wechat", timeout: float = 15.0) -> bytes | None:
    """拉取入站媒体原始字节。

    ref 是 http(s) 时直接拉取；否则按 platform 走对应 media host 的 /media/{ref}。
    """
    if ref.startswith("http://") or ref.startswith("https://"):
        url = ref
    else:
        media_host = _get_media_host(platform)
        if not media_host:
            LOG.error("fetch_media_bytes: media host 未配置 platform=%s", platform)
            return None
        url = f"{media_host}/media/{ref.lstrip('/')}"
    result = await async_get(url, timeout=timeout)
    if not result.ok:
        LOG.error("fetch_media_bytes 失败: ref=%s platform=%s err=%s", ref, platform, result.error or result.text)
        return None
    ct = result.headers.get("content-type", "")
    if "application/json" in ct or "text/" in ct:
        LOG.error("fetch_media_bytes 返回非媒体内容: ref=%s platform=%s content-type=%s", ref, platform, ct)
        return None
    return result.content


# ==================== 历史记录查询 ====================

async def query_history(chat_id: str, sender_id: str = "", sender_name: str = "",
                        limit: int = 500, platform: str = "wechat") -> list[dict]:
    payload = {"chat_id": chat_id, "limit": limit, "platform": platform}
    if sender_id:
        payload["sender_id"] = sender_id
    if sender_name:
        payload["sender_name"] = sender_name
    result = await _async_post("/query/history", payload, timeout=15.0)
    return result.get("data", {}).get("messages", [])


async def query_group_history(chat_id: str, limit: int = 1000,
                              platform: str = "wechat") -> list[dict]:
    result = await _async_post("/query/history", {
        "chat_id": chat_id, "limit": limit, "platform": platform,
    }, timeout=20.0)
    return result.get("data", {}).get("messages", [])
