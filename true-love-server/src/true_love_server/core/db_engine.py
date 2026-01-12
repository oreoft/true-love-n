# -*- coding: utf-8 -*-
"""
Database Engine - 数据库引擎
"""

import sqlite3
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


# ==================== 原有的 mc_devices 数据库逻辑 ====================

def create_db_and_table():
    """创建 mc_devices 表（原有逻辑）"""
    db_path = os.path.join(DBS_DIR, 'mc_devices.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS mc_devices (
        sender TEXT PRIMARY KEY,
        device_id TEXT NOT NULL
    );
    ''')
    conn.commit()
    conn.close()


# ==================== SQLAlchemy 数据库引擎（用于群消息记录）====================

# 数据库文件路径
DATABASE_URL = f"sqlite:///{DBS_DIR}/group_messages.db"

# 创建引擎
# SQLite 并发配置说明：
# - check_same_thread=False: 允许多线程使用同一连接
# - timeout=30: 等待锁释放的超时时间（秒）
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,  # SQLite 需要此配置
        "timeout": 30,  # 增加超时时间，等待锁释放
    },
    echo=False,  # 设置为 True 可以看到 SQL 日志
    pool_pre_ping=True,  # 检查连接是否有效
)

# 创建 Session 工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """初始化数据库，创建所有表"""
    try:
        Base.metadata.create_all(bind=engine)
        
        # 启用 WAL 模式，大幅改善并发写入性能
        # WAL 模式允许读写同时进行，减少 "database is locked" 错误
        with engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA busy_timeout=30000"))  # 30秒超时
            conn.execute(text("PRAGMA synchronous=NORMAL"))  # 平衡性能和安全
            conn.commit()
        
        LOG.info("Database initialized successfully with WAL mode: %s", DATABASE_URL)
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



