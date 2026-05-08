# -*- coding: utf-8 -*-
"""
Server DB 当前 Migration
历史记录见 db/migrations/*.sql 和 schema_migrations 表。

有新 migration 时：直接替换此文件内容即可，旧版本已在 schema_migrations 里记录，不会重复执行。
"""

import sqlite3


def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


# 对应 db/migrations/001_multi_platform.sql
VERSION = "001"
DESCRIPTION = "multi_platform: add platform/sender_id/sender_name/chat_name, drop sender"


def migrate(conn: sqlite3.Connection) -> None:
    """多平台支持：新增 platform/sender_id/sender_name/chat_name，回填，删旧列，建索引"""
    existing = _cols(conn, "group_messages")

    for col, typedef in [
        ("platform",    "VARCHAR(32)  NOT NULL DEFAULT 'wechat'"),
        ("sender_id",   "VARCHAR(128) NOT NULL DEFAULT ''"),
        ("sender_name", "VARCHAR(128) NOT NULL DEFAULT ''"),
        ("chat_name",   "VARCHAR(128) NOT NULL DEFAULT ''"),
    ]:
        if col not in existing:
            conn.execute(f"ALTER TABLE group_messages ADD COLUMN {col} {typedef}")

    if "sender" in existing:
        conn.execute("UPDATE group_messages SET sender_id   = sender WHERE sender_id   = ''")
        conn.execute("UPDATE group_messages SET sender_name = sender WHERE sender_name = ''")
    conn.execute("UPDATE group_messages SET chat_name = chat_id WHERE chat_name = ''")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_platform_chat ON group_messages (platform, chat_id)"
    )

    if "sender" in _cols(conn, "group_messages"):
        conn.execute("ALTER TABLE group_messages DROP COLUMN sender")


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
