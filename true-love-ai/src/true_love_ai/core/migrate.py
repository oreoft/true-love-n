# -*- coding: utf-8 -*-
"""
AI DB 当前 Migration
历史记录见 db/migrations/*.sql 和 schema_migrations 表。

有新 migration 时：直接替换此文件内容即可，旧版本已在 schema_migrations 里记录，不会重复执行。
"""

import sqlite3


def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


# 对应 db/migrations/002_dynamic_skills_add_permissions.sql
VERSION = "002"
DESCRIPTION = "dynamic_skills: add permissions column"


def migrate(conn: sqlite3.Connection) -> None:
    """dynamic_skills 表：新增 permissions 列（权限白名单 JSON 数组）"""
    if "permissions" not in _cols(conn, "dynamic_skills"):
        conn.execute("ALTER TABLE dynamic_skills ADD COLUMN permissions TEXT")


def run(db_path: str) -> None:
    """幂等执行当前 migration，已应用则跳过"""
    import logging
    log = logging.getLogger("migrate")

    conn = sqlite3.connect(db_path)
    try:
        applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
        if VERSION in applied:
            log.info("Migration %s: already applied, skipping", VERSION)
            return
        log.info("Migration %s: applying — %s", VERSION, DESCRIPTION)
        try:
            migrate(conn)
            from datetime import datetime
            conn.execute(
                "INSERT INTO schema_migrations (version, description, applied_at) VALUES (?, ?, ?)",
                (VERSION, DESCRIPTION, datetime.now().isoformat()),
            )
            conn.commit()
            log.info("Migration %s: done", VERSION)
        except Exception as e:
            conn.rollback()
            log.error("Migration %s: failed — %s", VERSION, e)
            raise
    finally:
        conn.close()
