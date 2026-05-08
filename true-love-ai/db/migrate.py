#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
true-love-ai DB 迁移脚本
对应 001_rename_sender_to_sender_id.sql

用法（在宿主机执行）：
  docker cp db/migrate.py tl-ai:/tmp/migrate.py
  docker exec tl-ai python3 /tmp/migrate.py
"""

import sqlite3
import sys

DB_PATH = "/app/dbs/ai_data.db"


def get_columns(conn, table):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def run():
    print(f"连接数据库: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)

    try:
        cols = get_columns(conn, "user_memory")
        print(f"user_memory 当前列: {sorted(cols)}\n")

        if "sender_id" in cols and "sender" not in cols:
            print("[SKIP] 已完成迁移：sender_id 存在，sender 不存在")
        elif "sender" in cols and "sender_id" not in cols:
            conn.execute("ALTER TABLE user_memory RENAME COLUMN sender TO sender_id")
            conn.commit()
            print("[OK]   重命名 sender → sender_id")
        elif "sender" in cols and "sender_id" in cols:
            print("[WARN] sender 和 sender_id 同时存在，请手动确认表结构！")
            sys.exit(1)
        else:
            print("[WARN] sender 和 sender_id 都不存在，请检查表结构！")
            sys.exit(1)

        final_cols = get_columns(conn, "user_memory")
        print(f"\n迁移完成！最终列: {sorted(final_cols)}")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] 迁移失败: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    run()
