# -*- coding: utf-8 -*-
"""
Action Routes - AI 回调接口

AI 侧 Agent 执行 skill 后，通过这些接口操作 WeChat（发消息、管理提醒、管理监听）。
所有接口均需要 token 验证。
"""

import logging

from fastapi import APIRouter

from .deps import verify_token
from .exception_handlers import ApiResponse, ValidationException
from ..services import base_client
from ..services.listen_manager import get_listen_manager
from ..services.scheduler_service import scheduler

LOG = logging.getLogger("ActionRoutes")


def _send_reminder(receiver: str, at_user: str, content: str, job_id: str) -> None:
    """模块级提醒触发函数（APScheduler SQLAlchemy jobstore 要求可序列化）"""
    LOG.info("提醒触发: job_id=%s, receiver=%s", job_id, receiver)
    try:
        success, msg = base_client.send_text(receiver, at_user, f"⏰ 【提醒功能】：\n\n{content}")
        if not success:
            LOG.error("提醒发送失败: %s", msg)
    except Exception as exc:
        LOG.exception("提醒触发异常: %s", exc)

action_router = APIRouter(prefix="/action")

listen_manager = get_listen_manager()


# ==================== 消息发送 ====================

@action_router.post("/send")
async def action_send(request: dict):
    """
    发送文本消息到 WeChat

    Body:
        - token: 鉴权 token
        - receiver: 接收者（群名或好友昵称）
        - content: 消息内容
        - at_user: 要@的用户昵称（可选，群聊时使用）
    """
    verify_token(request.get("token", ""))

    receiver = request.get("receiver", "")
    content = request.get("content", "")
    at_user = request.get("at_user", "")

    if not receiver or not content:
        raise ValidationException("receiver 和 content 不能为空")

    LOG.info("action/send: receiver=%s, at_user=%s, content=%s", receiver, at_user, content[:50])
    success, error_msg = base_client.send_text(receiver, at_user, content)

    if not success:
        raise ValidationException(f"消息发送失败: {error_msg}")

    return ApiResponse(data=None)


@action_router.post("/send-file")
async def action_send_file(request: dict):
    """
    发送文件/图片/视频到 WeChat

    Body:
        - token: 鉴权 token
        - receiver: 接收者
        - path: 文件路径（Server 本地路径）
        - file_type: 文件类型 image | video | file（默认 image）
    """
    verify_token(request.get("token", ""))

    receiver = request.get("receiver", "")
    path = request.get("path", "")
    file_type = request.get("file_type", "image")

    if not receiver or not path:
        raise ValidationException("receiver 和 path 不能为空")

    LOG.info("action/send-file: receiver=%s, type=%s, path=%s", receiver, file_type, path)

    if file_type == "video":
        success, error_msg = base_client.send_video(path, receiver)
    else:
        success, error_msg = base_client.send_img(path, receiver)

    if not success:
        raise ValidationException(f"文件发送失败: {error_msg}")

    return ApiResponse(data=None)


# ==================== 提醒管理 ====================

@action_router.post("/reminder/add")
async def action_add_reminder(request: dict):
    """
    添加定时提醒任务

    Body:
        - token: 鉴权 token
        - job_id: 唯一任务 ID
        - target_time_iso: ISO-8601 触达时间（含时区，如 2026-04-14T10:30:00+08:00）
        - receiver: 发送目标（群名或好友昵称）
        - at_user: 要@的用户（可选）
        - content: 提醒内容
    """
    verify_token(request.get("token", ""))

    job_id = request.get("job_id", "")
    target_time_iso = request.get("target_time_iso", "")
    receiver = request.get("receiver", "")
    at_user = request.get("at_user", "")
    content = request.get("content", "")

    if not job_id or not target_time_iso or not receiver or not content:
        raise ValidationException("job_id、target_time_iso、receiver、content 均不能为空")

    try:
        import dateutil.parser
        from datetime import datetime
        dt = dateutil.parser.isoparse(target_time_iso)
        now = datetime.now(dt.tzinfo)
        if dt <= now:
            raise ValidationException(f"目标时间 {target_time_iso} 已是过去时间")
    except ValidationException:
        raise
    except Exception as e:
        raise ValidationException(f"时间格式解析失败: {target_time_iso}, 错误: {e}")

    scheduler.add_job(
        _send_reminder,
        'date',
        run_date=dt,
        id=job_id,
        replace_existing=True,
        kwargs={"receiver": receiver, "at_user": at_user, "content": content, "job_id": job_id},
    )
    LOG.info("action/reminder/add: job_id=%s, time=%s, receiver=%s", job_id, target_time_iso, receiver)
    return ApiResponse(data={"job_id": job_id})


@action_router.post("/reminder/delete")
async def action_delete_reminder(request: dict):
    """
    删除定时提醒任务

    Body:
        - token: 鉴权 token
        - job_id: 要删除的任务 ID
    """
    verify_token(request.get("token", ""))

    job_id = request.get("job_id", "")
    if not job_id:
        raise ValidationException("job_id 不能为空")

    job = scheduler.get_job(job_id)
    if not job:
        raise ValidationException(f"未找到提醒任务: {job_id}")

    scheduler.remove_job(job_id)
    LOG.info("action/reminder/delete: job_id=%s", job_id)
    return ApiResponse(data=None)


@action_router.post("/reminder/query")
async def action_query_reminder(request: dict):
    """
    查询指定接收者的未执行提醒列表

    Body:
        - token: 鉴权 token
        - receiver: 接收者（用于过滤，只返回该接收者的提醒）
    """
    verify_token(request.get("token", ""))

    receiver = request.get("receiver", "")

    jobs = scheduler.get_jobs()
    result = []
    for job in jobs:
        # 过滤出属于该 receiver 的提醒（_trigger 闭包里的 receiver 无法直接拿到，用 job_id 前缀约定）
        # job_id 格式：reminder_{receiver}_{timestamp}（由 AI 侧生成）
        if receiver and not job.id.startswith(f"reminder_{receiver}_"):
            continue
        if job.next_run_time:
            result.append({
                "job_id": job.id,
                "next_run_time": job.next_run_time.isoformat(),
            })

    LOG.info("action/reminder/query: receiver=%s, count=%d", receiver, len(result))
    return ApiResponse(data={"jobs": result})


# ==================== 监听管理 ====================

@action_router.post("/listen/add")
async def action_listen_add(request: dict):
    """
    添加 WeChat 监听

    Body:
        - token: 鉴权 token
        - chat_name: 聊天对象名称
    """
    verify_token(request.get("token", ""))

    chat_name = request.get("chat_name", "")
    if not chat_name:
        raise ValidationException("chat_name 不能为空")

    result = listen_manager.add_listen(chat_name)
    if not result.get("success"):
        raise ValidationException(result.get("message", "添加监听失败"))

    LOG.info("action/listen/add: chat_name=%s", chat_name)
    return ApiResponse(data=result)


@action_router.post("/listen/remove")
async def action_listen_remove(request: dict):
    """
    移除 WeChat 监听

    Body:
        - token: 鉴权 token
        - chat_name: 聊天对象名称
    """
    verify_token(request.get("token", ""))

    chat_name = request.get("chat_name", "")
    if not chat_name:
        raise ValidationException("chat_name 不能为空")

    result = listen_manager.remove_listen(chat_name)
    if not result.get("success"):
        raise ValidationException(result.get("message", "移除监听失败"))

    LOG.info("action/listen/remove: chat_name=%s", chat_name)
    return ApiResponse(data=result)
