# -*- coding: utf-8 -*-
"""
Routes - 路由定义

定义所有 HTTP 接口路由。
"""

import logging
import time
from pathlib import Path

import requests

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse

from .deps import verify_token
from .exception_handlers import ApiResponse, ValidationException
from ..core import Config
from ..models import ChatMsg
from ..services import base_client
from ..services.listen_manager import get_listen_manager
from ..services.loki_client import get_loki_client
from ..services.group_message_repository import GroupMessageRepository

LOG = logging.getLogger("Routes")

router = APIRouter()

# 获取 ListenManager 单例
listen_manager = get_listen_manager()

_MEDIA_ROOT = Path("wx_imgs")


@router.get("/media/{file_path:path}")
async def get_media(file_path: str, token: str = Query(...)):
    """提供 wx_imgs 目录下的媒体文件（供 AI 服务跨机读取）"""
    verify_token(token)
    safe = (_MEDIA_ROOT / file_path).resolve()
    if not str(safe).startswith(str(_MEDIA_ROOT.resolve())):
        raise ValidationException("forbidden")
    if not safe.exists():
        raise ValidationException("not found")
    return FileResponse(safe)


@router.get("/ping")
async def ping():
    """简单存活检查"""
    return "pong"


@router.get("/health")
async def health():
    """Docker 健康检查接口"""
    return {"status": "ok", "service": "true-love-server"}


@router.post("/send-msg")
async def send_msg(request: dict):
    """
    推送消息接口

    供外部调用，发送消息到指定接收者。
    """
    LOG.info("推送消息收到请求, req: %s", request)

    # 验证 token
    verify_token(request.get('token', ''))

    http_config = Config().HTTP or {}
    send_receiver = request.get('sendReceiver')
    at_receiver = request.get('atReceiver')
    content = request.get('content')
    receiver_map = http_config.get("receiver_map", {})

    # 判断是否合法发送人
    if not receiver_map.get(send_receiver) or not content:
        raise ValidationException("诶嘿~接收者没注册或者内容是空的呢，检查一下吧~")

    # 开始发送（同步接口，失败需要返回错误）
    success, error_msg = base_client.send_text(
        receiver_map.get(send_receiver, ""),
        receiver_map.get(at_receiver, ""),
        content
    )

    if not success:
        raise ValidationException(f"呜呜~消息发送失败了捏: {error_msg}")

    return ApiResponse(data=None)


@router.post("/on-message")
async def on_message(
        request: dict,
        background_tasks: BackgroundTasks,
):
    """
    消息统一入口（Base 无脑转发所有消息）：
    - 所有消息存 DB
    - is_at_me 或私聊才触发 AI 处理
    - 通过 save() 返回值去重，防止重复触发 AI
    """
    LOG.info("聊天消息收到请求, req: %s", request)

    verify_token(request.get('token', ''))

    msg = ChatMsg.from_dict(request)
    background_tasks.add_task(_handle_incoming_message, msg)

    return ApiResponse(data="")


def _handle_incoming_message(msg: ChatMsg) -> None:
    """存储消息（best-effort）并按需触发 AI，两个逻辑互相独立"""
    try:
        from ..core.db_engine import SessionLocal
        with SessionLocal() as db:
            GroupMessageRepository(db).save(msg)
    except Exception as e:
        LOG.error(f"消息存储失败: {e}", exc_info=True)

    if msg.is_at_me or not msg.is_group:
        try:
            _trigger_ai(msg)
        except Exception as e:
            LOG.error(f"触发 AI 失败: {e}", exc_info=True)


def _trigger_ai(msg: ChatMsg) -> None:
    """Fire-and-forget POST 到 AI 的 /trigger 接口"""
    ai_host = (Config().AI_SERVICE or {}).get("host", "").rstrip("/")
    if not ai_host:
        LOG.warning("AI_SERVICE.host 未配置，跳过 AI 触发")
        return

    token = (Config().HTTP_TOKEN or [""])[0]
    payload = {
        "token": token,
        "msg": msg.to_dict(),
    }
    try:
        from true_love_server.core.trace import get_trace_id
        resp = requests.post(
            f"{ai_host}/trigger",
            json=payload,
            headers={"X-Trace-ID": get_trace_id()},
            timeout=(5,10),
        )
        resp.raise_for_status()
        LOG.info("AI trigger 成功: sender=%s", msg.sender)
    except Exception as e:
        LOG.error("AI trigger 失败: sender=%s, err=%s", msg.sender, e)


# ==================== 查询接口（供 AI 回调使用）====================

@router.post("/query/history")
async def query_history(request: dict):
    """
    查询群消息历史（供 AI 的 analyze_speech skill 调用）

    Body:
        - token: 鉴权 token
        - chat_id: 群聊 ID
        - sender: 发送者昵称
        - limit: 最大返回条数（默认100）
    """
    verify_token(request.get("token", ""))

    chat_id = request.get("chat_id", "")
    sender = request.get("sender", "")
    limit = int(request.get("limit", 100))

    if not chat_id or not sender:
        raise ValidationException("chat_id 和 sender 不能为空")

    from ..core.db_engine import SessionLocal
    with SessionLocal() as db:
        messages = GroupMessageRepository(db).get_recent_messages(chat_id, sender, limit)

    LOG.info("query/history: chat_id=%s, sender=%s, count=%d", chat_id, sender, len(messages))
    return ApiResponse(data={"messages": messages})


# ==================== Listen 监听管理接口 ====================

@router.get("/admin/listen/status")
async def get_listen_status():
    """
    获取监听状态
    
    状态定义（只有两种）：
    - healthy: 子窗口存在 AND ChatInfo 能正确响应
    - unhealthy: 子窗口不存在 OR ChatInfo 无法响应
    
    Returns:
        - listeners: 每个监听的状态列表
        - summary: 状态汇总 {"healthy": N, "unhealthy": M}
    """
    result = listen_manager.get_listener_status()
    return ApiResponse(data=result)


@router.post("/admin/listen/add")
async def add_listen(request: dict):
    """
    添加监听的聊天对象
    
    Request Body:
        - chat_name: 聊天对象名称（好友昵称或群名）
    """
    chat_name = request.get('chat_name', '')
    if not chat_name:
        raise ValidationException("chat_name 不能为空哦~")

    result = listen_manager.add_listen(chat_name)
    if not result.get("success"):
        raise ValidationException(result.get("message", "添加监听失败"))

    return ApiResponse(data=result)


@router.post("/admin/listen/remove")
async def remove_listen(request: dict):
    """
    移除监听的聊天对象
    
    Request Body:
        - chat_name: 聊天对象名称
    """
    chat_name = request.get('chat_name', '')
    if not chat_name:
        raise ValidationException("chat_name 不能为空哦~")

    result = listen_manager.remove_listen(chat_name)
    if not result.get("success"):
        raise ValidationException(result.get("message", "移除监听失败"))
    return ApiResponse(data=result)


@router.post("/admin/listen/refresh")
async def refresh_listen():
    """
    智能刷新监听列表
    
    流程：
    1. 获取监听状态
    2. healthy 的跳过，unhealthy 的执行 reset
    
    Returns:
        - total: 总监听数
        - success_count: 成功数
        - fail_count: 失败数
        - listeners: 每个监听的详情列表
    """
    result = listen_manager.refresh_listen()
    # refresh 返回的是统计结果，根据 fail_count 判断是否有失败
    if result.get("fail_count", 0) > 0:
        raise ValidationException(f"刷新部分失败: {result.get('fail_count')} 个监听恢复失败")
    return ApiResponse(data=result)


@router.post("/admin/listen/reset")
async def reset_listen(request: dict):
    """
    重置单个监听
    
    通过关闭子窗口、移除监听、重新添加监听的方式恢复异常的监听。
    
    Request Body:
        - chat_name: 聊天对象名称
        
    Returns:
        - success: 是否成功
        - message: 结果描述
        - steps: 各步骤执行情况
    """
    chat_name = request.get('chat_name', '')
    if not chat_name:
        raise ValidationException("chat_name 不能为空哦~")

    result = listen_manager.reset_listener(chat_name)
    if not result.get("success"):
        raise ValidationException(result.get("message", "重置监听失败"))
    return ApiResponse(data=result)


@router.post("/admin/listen/reset-all")
async def reset_all_listen():
    """
    重置所有监听
    
    通过停止所有监听、关闭所有子窗口、刷新 UI、重新添加所有监听的方式恢复。
    
    Returns:
        - success: 是否成功
        - message: 结果描述
        - total: 总监听数
        - recovered: 成功恢复的列表
        - failed: 恢复失败的列表
        - steps: 各步骤执行情况
    """
    result = listen_manager.reset_all_listeners()
    if not result.get("success"):
        raise ValidationException(result.get("message", "重置所有监听失败"))
    return ApiResponse(data=result)


@router.post("/admin/listen/get-all-message")
async def get_all_message(request: dict):
    """
    测活接口 - 获取聊天窗口的所有消息
    
    调用 Base 的 execute/chat 接口，执行 GetAllMessage 方法。
    
    Request Body:
        - chat_name: 聊天对象名称
        
    Returns:
        - success: 是否成功
        - data: 消息列表
        - message: 结果描述
    """
    chat_name = request.get('chat_name', '')
    if not chat_name:
        raise ValidationException("chat_name 不能为空哦~")

    result = base_client.execute_chat(chat_name, "GetAllMessage", {})
    if not result.get("success"):
        raise ValidationException(result.get("message", "获取消息失败"))
    return ApiResponse(data=result)


# ==================== Job 手动触发接口 ====================

_JOB_MAP = None


def _get_job_map() -> dict:
    global _JOB_MAP
    if _JOB_MAP is None:
        from ..jobs import job_process as jp
        _JOB_MAP = {
            "notice_moyu_schedule": jp.notice_moyu_schedule,
            "notice_usa_moyu_schedule": jp.notice_usa_moyu_schedule,
            "download_moyu_file": jp.download_moyu_file,
            "download_zao_bao_file": jp.download_zao_bao_file,
            "notice_test": jp.notice_test,
            "notice_mei_yuan": jp.notice_mei_yuan,
            "notice_library_schedule": jp.notice_library_schedule,
            "notice_ao_yuan_schedule": jp.notice_ao_yuan_schedule,
        }
    return _JOB_MAP


@router.post("/action/job/run")
async def run_job(request: dict, background_tasks: BackgroundTasks):
    """
    手动触发定时任务

    Request Body:
        - job_name: 任务名称
    """
    verify_token(request.get("token", ""))
    job_name = request.get("job_name", "").strip()
    job_map = _get_job_map()

    if not job_name:
        raise ValidationException(f"job_name 不能为空，可选: {list(job_map.keys())}")
    if job_name not in job_map:
        raise ValidationException(f"未知 job: {job_name}，可选: {list(job_map.keys())}")

    background_tasks.add_task(job_map[job_name])
    LOG.info("手动触发 job: %s", job_name)
    return ApiResponse(data={"job_name": job_name, "status": "triggered"})


# ==================== Loki 日志查询接口 ====================

@router.get("/admin/loki/logs")
async def query_loki_logs(
        start_ms: int = None,
        end_ms: int = None,
        limit: int = 500,
        direction: str = 'backward'
):
    """
    查询 Loki 日志
    
    Query Parameters:
        - start_ms: 开始时间（毫秒时间戳），默认为 end_ms 前 5 分钟
        - end_ms: 结束时间（毫秒时间戳），默认为当前时间
        - limit: 最大返回条数，默认 500
        - direction: 排序方向 forward(旧→新) / backward(新→旧)，默认 backward
    
    Returns:
        - logs: 日志列表 [{timestamp, time_str, level, service, content, raw}, ...]
        - earliest_ms: 返回数据中最早的毫秒时间戳
        - latest_ms: 返回数据中最新的毫秒时间戳
        - query_start_ms: 本次查询的开始时间
        - query_end_ms: 本次查询的结束时间
    """
    now_ms = int(time.time() * 1000)

    # 默认值处理
    if end_ms is None:
        end_ms = now_ms
    if start_ms is None:
        start_ms = end_ms - 60 * 60 * 1000  # 默认 1 小时

    # 转换为纳秒
    start_ns = start_ms * 1_000_000
    end_ns = end_ms * 1_000_000

    loki_client = get_loki_client()
    result = loki_client.query_range(start_ns, end_ns, limit, direction)

    if not result["success"]:
        raise ValidationException(result["message"])

    # 转换 LogEntry 为 dict
    logs = [entry.to_dict() for entry in result["logs"]]

    return ApiResponse(data={
        "logs": logs,
        "earliest_ms": result["earliest_ns"] // 1_000_000,
        "latest_ms": result["latest_ns"] // 1_000_000,
        "query_start_ms": start_ms,
        "query_end_ms": end_ms,
        "count": len(logs)
    })
