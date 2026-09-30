# -*- coding: utf-8 -*-
"""
Task Service - 定时任务

后台"定时任务"页里的第二种类型：把写好的任务（如国内摸鱼）推给一批接收者，
可以只执行一次，也可以每天定时执行。和提醒共用同一个 APScheduler，存在这台 server 的数据库里。
"""
import json
import logging
import re
import uuid
from datetime import datetime
from typing import Any

import pytz
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from .scheduler_service import scheduler

LOG = logging.getLogger("TaskService")

ID_PREFIX = "task_"
ONCE = "once"
DAILY = "daily"

TIMEZONES = {
    "Asia/Shanghai": "北京时间",
    "America/Chicago": "美中时间",
}

# 设置页里原来的推送群 → 迁移成的每天任务
_LEGACY_SETTINGS = {
    "moyu_groups": ("notice_moyu_schedule", "09:05", "Asia/Shanghai"),
    "usa_moyu_groups": ("notice_usa_moyu_schedule", "08:00", "America/Chicago"),
}


def _job_process():
    from ..jobs import job_process
    return job_process


def _run_task(task_id: str, job_name: str, receivers: list[str], schedule: dict) -> None:
    """APScheduler 触发函数（模块级，SQLAlchemy jobstore 按名字引用）"""
    LOG.info("定时任务触发: task_id=%s job=%s receivers=%s", task_id, job_name, receivers)
    _job_process().run_task(job_name, receivers)


def _clean(job_name: str, receivers: Any, schedule: Any) -> tuple[str, list[str], dict, Any]:
    """校验表单，返回 (方法名, 接收者, 触发方式, APScheduler trigger)；不合法时抛 ValueError"""
    job_name = str(job_name or "").strip()
    _job_process().find_task(job_name)

    if not isinstance(receivers, list):
        raise ValueError("接收者必须是列表")
    receivers = list(dict.fromkeys(str(name).strip() for name in receivers if str(name).strip()))
    if not receivers:
        raise ValueError("至少要有一个接收者")

    schedule = schedule if isinstance(schedule, dict) else {}
    mode = schedule.get("mode")
    if mode == ONCE:
        import dateutil.parser
        try:
            run_at = dateutil.parser.isoparse(str(schedule.get("run_at", "")))
        except ValueError:
            raise ValueError("执行时间格式不对")
        if run_at.tzinfo is None:
            raise ValueError("执行时间必须带时区")
        if run_at <= datetime.now(run_at.tzinfo):
            raise ValueError("执行时间已经过去了")
        return job_name, receivers, {"mode": ONCE, "run_at": run_at.isoformat()}, DateTrigger(run_date=run_at)

    if mode == DAILY:
        at = str(schedule.get("time", "")).strip()
        match = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", at)
        if not match:
            raise ValueError("每天执行的时间格式应为 HH:MM")
        timezone = schedule.get("timezone", "")
        if timezone not in TIMEZONES:
            raise ValueError(f"不支持的时区: {timezone}")
        hour, minute = int(match.group(1)), int(match.group(2))
        trigger = CronTrigger(hour=hour, minute=minute, timezone=pytz.timezone(timezone))
        return job_name, receivers, {"mode": DAILY, "time": f"{hour:02d}:{minute:02d}", "timezone": timezone}, trigger

    raise ValueError("触发方式只能是单次或每天")


def _schedule_job(task_id: str, job_name: str, receivers: Any, schedule: Any) -> dict:
    job_name, receivers, schedule, trigger = _clean(job_name, receivers, schedule)
    job = scheduler.add_job(
        _run_task,
        trigger,
        id=task_id,
        replace_existing=True,
        max_instances=1,
        kwargs={"task_id": task_id, "job_name": job_name, "receivers": receivers, "schedule": schedule},
    )
    return _describe(job)


def _describe(job) -> dict:
    kwargs = job.kwargs or {}
    return {
        "task_id": job.id,
        "job_name": kwargs.get("job_name", ""),
        "receivers": list(kwargs.get("receivers", [])),
        "schedule": dict(kwargs.get("schedule", {})),
        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else "",
    }


def _get(task_id: str):
    job = scheduler.get_job(task_id) if task_id.startswith(ID_PREFIX) else None
    if not job:
        raise ValueError(f"未找到定时任务: {task_id}")
    return job


def job_names() -> list[str]:
    """可选的推送任务方法名，后台输入框用来提示"""
    return _job_process().task_names()


def list_tasks() -> list[dict]:
    """全部定时任务，按下次执行时间升序"""
    result = [_describe(job) for job in scheduler.get_jobs() if job.id.startswith(ID_PREFIX)]
    result.sort(key=lambda task: task["next_run_time"] or "9999")
    return result


def add_task(job_name: str, receivers: Any, schedule: Any) -> dict:
    task_id = f"{ID_PREFIX}{job_name}_{uuid.uuid4().hex[:8]}"
    task = _schedule_job(task_id, job_name, receivers, schedule)
    LOG.info("task/add: %s", task)
    return task


def update_task(task_id: str, job_name: str, receivers: Any, schedule: Any) -> dict:
    _get(task_id)
    task = _schedule_job(task_id, job_name, receivers, schedule)
    LOG.info("task/update: %s", task)
    return task


def delete_task(task_id: str) -> dict:
    _get(task_id)
    scheduler.remove_job(task_id)
    LOG.info("task/delete: task_id=%s", task_id)
    return {"task_id": task_id}


def run_now(task_id: str) -> dict:
    """立即执行一次，不影响之后的定时"""
    kwargs = dict(_get(task_id).kwargs or {})
    _start(kwargs)
    LOG.info("task/run: task_id=%s", task_id)
    return {"task_id": task_id}


def run_by_job_name(job_name: str) -> list[str]:
    """立即执行这个任务名下的所有定时任务（AI 手动触发用），返回执行了的 task_id"""
    _job_process().find_task(job_name)
    started = []
    for job in scheduler.get_jobs():
        kwargs = dict(job.kwargs or {})
        if job.id.startswith(ID_PREFIX) and kwargs.get("job_name") == job_name:
            _start(kwargs)
            started.append(job.id)
    LOG.info("task/run_by_job_name: job=%s tasks=%s", job_name, started)
    return started


def _start(kwargs: dict) -> None:
    """在调度器的线程池里执行，推送要几十秒，不阻塞接口"""
    scheduler.add_job(_run_task, kwargs=kwargs, jobstore="memory")


def import_from_settings() -> None:
    """
    设置页原来的两组推送群迁移成每天执行的定时任务

    迁移完删掉旧设置，所以只会迁移一次；旧设置不存在时什么都不做。
    """
    from ..core.db_engine import SessionLocal
    from ..models.setting import Setting

    with SessionLocal() as db:
        for key, (job_name, at, timezone) in _LEGACY_SETTINGS.items():
            row = db.get(Setting, key)
            if row is None:
                continue
            groups = json.loads(row.value)
            if groups:
                task = add_task(job_name, groups, {"mode": DAILY, "time": at, "timezone": timezone})
                LOG.info("setting [%s] migrated to task %s", key, task)
            db.delete(row)
            db.commit()
