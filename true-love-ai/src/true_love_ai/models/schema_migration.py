# -*- coding: utf-8 -*-
"""
Schema Migration 记录模型

记录已执行的数据库 migration 版本，由 create_all() 统一建表。
"""

from datetime import datetime

from sqlalchemy import Column, String, DateTime

from true_love_ai.core.db_engine import Base


class SchemaMigration(Base):
    """Migration 版本记录表"""

    __tablename__ = "schema_migrations"

    version     = Column(String(32),  primary_key=True, comment="Migration 版本号")
    description = Column(String(256), nullable=False,   comment="Migration 描述")
    applied_at  = Column(DateTime,    nullable=False, default=datetime.now, comment="执行时间")
