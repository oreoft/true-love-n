# -*- coding: utf-8 -*-
"""
Server DB 当前 Migration
已执行过的版本记录在 schema_migrations 表里。

有新 migration 时：直接替换此文件内容即可，旧版本已在 schema_migrations 里记录，不会重复执行。
"""

import sqlite3


def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


# 监听列表从共享文件搬进数据库
VERSION = "002"
DESCRIPTION = "listen_chats: import listen_chats.json into the listen_chats table"

# 旧版 base 工作目录下的监听列表，docker-compose 软链到 server 工作目录
LEGACY_LISTEN_FILE = "listen_chats.json"


def migrate(conn: sqlite3.Connection) -> None:
    """把旧的 listen_chats.json 导入 listen_chats 表，文件不存在时什么都不导"""
    import json
    import os
    from datetime import datetime, timedelta

    if not os.path.exists(LEGACY_LISTEN_FILE):
        return
    with open(LEGACY_LISTEN_FILE, encoding="utf-8") as f:
        chats = json.load(f)
    if not isinstance(chats, list):
        return

    # 按文件里的顺序递增加入时间，base 会按这个顺序注册监听
    start = datetime.now()
    for i, chat_name in enumerate(dict.fromkeys(str(c) for c in chats if c)):
        conn.execute(
            "INSERT OR IGNORE INTO listen_chats (chat_name, created_at) VALUES (?, ?)",
            (chat_name, (start + timedelta(microseconds=i)).strftime("%Y-%m-%d %H:%M:%S.%f")),
        )


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
