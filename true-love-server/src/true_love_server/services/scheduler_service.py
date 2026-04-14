# -*- coding: utf-8 -*-
"""
Scheduler Service - 定时任务调度服务
内部管理 APScheduler，并持久化到 SQLite 中（借用 DB Engine 实例）
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from ..core.db_engine import engine

LOG = logging.getLogger("SchedulerService")

# 初始化配置与 Job Store（表名暂定 apscheduler_jobs）
_jobstores = {
    'default': SQLAlchemyJobStore(engine=engine, tablename='apscheduler_jobs')
}
_executors = {
    'default': ThreadPoolExecutor(20)
}
_job_defaults = {
    'coalesce': False,
    'max_instances': 3
}

# 全局单例调度器
scheduler = BackgroundScheduler(
    jobstores=_jobstores,
    executors=_executors,
    job_defaults=_job_defaults,
    timezone='UTC'  # 底层全都走 UTC 标准记录，触发时再处理
)

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        LOG.info("Global persistent APScheduler has started (SQLAlchemyJobStore).")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        LOG.info("Global persistent APScheduler has gracefully shutdown.")
