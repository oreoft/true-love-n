# -*- coding: utf-8 -*-
"""
AI 数据库引擎

管理 AI 侧 SQLite 数据库（用户画像）。
"""

import logging
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

LOG = logging.getLogger("DBEngine")

DBS_DIR = "dbs"
os.makedirs(DBS_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{DBS_DIR}/ai_data.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    """初始化数据库，建表"""
    try:
        # 导入所有 ORM model 以注册到 Base.metadata
        from true_love_ai.models.user_memory import UserMemory  # noqa: F401
        from true_love_ai.models.session_message import SessionMessage  # noqa: F401
        from true_love_ai.models.dynamic_skill import DynamicSkill  # noqa: F401

        Base.metadata.create_all(bind=engine)

        with engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.commit()

        LOG.info("AI Database initialized: %s", DATABASE_URL)
    except Exception as e:
        LOG.error("AI Database init failed: %s", e)
        raise
