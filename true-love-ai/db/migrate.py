# -*- coding: utf-8 -*-
"""
AI DB 当前 Migration
历史记录见 db/migrations/*.sql 和 schema_migrations 表。

有新 migration 时：直接替换此文件内容即可，旧版本已在 schema_migrations 里记录，不会重复执行。
"""

import sqlite3


def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


# 对应 db/migrations/001_rename_sender_to_sender_id.sql
VERSION = "001"
DESCRIPTION = "user_memory: rename sender to sender_id"


def migrate(conn: sqlite3.Connection) -> None:
    """user_memory 表：将 sender 列重命名为 sender_id"""
    existing = _cols(conn, "user_memory")
    if "sender" in existing and "sender_id" not in existing:
        conn.execute("ALTER TABLE user_memory RENAME COLUMN sender TO sender_id")


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
            conn.execute(
                "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                (VERSION, DESCRIPTION),
            )
            conn.commit()
            log.info("Migration %s: done", VERSION)
        except Exception as e:
            conn.rollback()
            log.error("Migration %s: failed — %s", VERSION, e)
            raise
    finally:
        conn.close()
