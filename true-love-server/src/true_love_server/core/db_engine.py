# -*- coding: utf-8 -*-
"""
Database Engine - 数据库引擎
"""

import logging
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from ..models.group_message import Base

LOG = logging.getLogger("DBEngine")

# ==================== 数据库目录配置 ====================

import os

# 数据库目录（统一管理所有 .db 文件）
DBS_DIR = "dbs"

# 确保目录存在
os.makedirs(DBS_DIR, exist_ok=True)


# ==================== SQLAlchemy 数据库引擎 ====================

# 数据库文件路径
DATABASE_URL = f"sqlite:///{DBS_DIR}/group_messages.db"

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite 多线程需要此配置
    echo=False,  # 设置为 True 可以看到 SQL 日志
)

# 创建 Session 工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """初始化数据库，创建所有表"""
    try:
        Base.metadata.create_all(bind=engine)
        
        # 启用 WAL 模式，改善并发写入性能
        with engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.commit()
        
        LOG.info("Database initialized with WAL mode: %s", DATABASE_URL)
    except Exception as e:
        LOG.error("Failed to initialize database: %s", e)
        raise


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库 Session（用于依赖注入）
    
    使用方式:
        @router.post("/xxx")
        async def xxx(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



