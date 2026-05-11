# -*- coding: utf-8 -*-
"""
Reminder Service - 定时提醒业务逻辑

action_routes（AI 回调，有 token）和 routes（Admin 后台，无 token）共用此模块。
"""
import asyncio
import logging
import time

from .scheduler_service import scheduler

LOG = logging.getLogger("ReminderService")


def _send_reminder(receiver: str, at_user: str, content: str, job_id: str,
                   platform: str = "wechat") -> None:
    """APScheduler 触发函数（模块级，SQLAlchemy jobstore 要求可序列化）"""
    LOG.info("提醒触发: job_id=%s, platform=%s, receiver=%s", job_id, platform, receiver)
    try:
        from ..services import base_client
        success, msg = asyncio.run(base_client.send_text(
            receiver,
            at_user,
            f"⏰ 【提醒功能】：\n\n{content}",
            platform=platform,
        ))
        if not success:
            LOG.error("提醒发送失败: %s", msg)
    except Exception as exc:
        LOG.exception("提醒触发异常: %s", exc)


def _parse_future_dt(iso_str: str):
    """解析 ISO-8601 时间字符串，校验必须是未来时间，返回 datetime 对象。"""
    import dateutil.parser
    from datetime import datetime
    dt = dateutil.parser.isoparse(iso_str)
    now = datetime.now(dt.tzinfo)
    if dt <= now:
        raise ValueError(f"目标时间 {iso_str} 已是过去时间")
    return dt


def add_reminder(job_id: str, target_time_iso: str, receiver: str,
                 content: str, at_user: str = "", platform: str = "wechat") -> dict:
    """新增或覆盖提醒任务，返回 {"job_id": ...}。"""
    dt = _parse_future_dt(target_time_iso)
    scheduler.add_job(
        _send_reminder,
        'date',
        run_date=dt,
        id=job_id,
        replace_existing=True,
        kwargs={
            "receiver": receiver,
            "at_user": at_user,
            "content": content,
            "job_id": job_id,
            "platform": platform,
        },
    )
    LOG.info("reminder/add: job_id=%s platform=%s time=%s receiver=%s",
             job_id, platform, target_time_iso, receiver)
    return {"job_id": job_id}


def delete_reminder(job_id: str) -> dict:
    """删除提醒任务，job 不存在时抛 ValueError。"""
    job = scheduler.get_job(job_id)
    if not job:
        raise ValueError(f"未找到提醒任务: {job_id}")
    scheduler.remove_job(job_id)
    LOG.info("reminder/delete: job_id=%s", job_id)
    return {"job_id": job_id}


def update_reminder(job_id: str, new_time_iso: str = "", new_content: str = "") -> dict:
    """修改提醒的时间或内容（至少一个），返回 {"job_id": ..., "next_run_time": ...}。"""
    if not new_time_iso and not new_content:
        raise ValueError("new_time_iso 和 new_content 至少提供一个")

    job = scheduler.get_job(job_id)
    if not job:
        raise ValueError(f"未找到提醒任务: {job_id}")

    old_kwargs = dict(job.kwargs or {})
    dt = _parse_future_dt(new_time_iso) if new_time_iso else job.next_run_time
    new_kwargs = {**old_kwargs, "content": new_content or old_kwargs.get("content", "")}

    scheduler.remove_job(job_id)
    scheduler.add_job(
        _send_reminder,
        'date',
        run_date=dt,
        id=job_id,
        kwargs=new_kwargs,
    )
    LOG.info("reminder/update: job_id=%s new_time=%s new_content=%s",
             job_id, dt.isoformat(), new_kwargs.get("content", ""))
    return {"job_id": job_id, "next_run_time": dt.isoformat()}


def query_reminders(receiver: str = "", platform: str = "wechat") -> list[dict]:
    """按 receiver + platform 过滤查询（AI 用），返回精简字段列表。"""
    jobs = scheduler.get_jobs()
    result = []
    for job in jobs:
        if receiver and not job.id.startswith(f"reminder_{receiver}_"):
            continue
        if (job.kwargs or {}).get("platform", "wechat") != platform:
            continue
        if job.next_run_time:
            kwargs = job.kwargs or {}
            result.append({
                "job_id": job.id,
                "content": kwargs.get("content", ""),
                "next_run_time": job.next_run_time.isoformat(),
            })
    return result


def list_all_reminders() -> list[dict]:
    """全量列出所有待执行提醒（Admin 用），含完整字段，按时间升序。"""
    jobs = scheduler.get_jobs()
    result = []
    for job in jobs:
        if not job.id.startswith("reminder_"):
            continue
        if not job.next_run_time:
            continue
        kwargs = job.kwargs or {}
        result.append({
            "job_id": job.id,
            "receiver": kwargs.get("receiver", ""),
            "content": kwargs.get("content", ""),
            "at_user": kwargs.get("at_user", ""),
            "platform": kwargs.get("platform", "wechat"),
            "next_run_time": job.next_run_time.isoformat(),
        })
    result.sort(key=lambda x: x["next_run_time"])
    return result


def make_job_id(receiver: str) -> str:
    """生成提醒任务 ID。"""
    return f"reminder_{receiver}_{int(time.time())}"
