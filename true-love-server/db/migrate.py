#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
true-love-server DB 迁移脚本
对应 002_multi_platform.sql

用法（在宿主机执行）：
  docker cp db/migrate.py tl-server:/tmp/migrate.py
  docker exec tl-server python3 /tmp/migrate.py
"""

import sqlite3
import sys

DB_PATH = "/app/dbs/group_messages.db"


def get_columns(conn, table):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def get_indexes(conn, table):
    cur = conn.execute(f"PRAGMA index_list({table})")
    return {row[1] for row in cur.fetchall()}


def run():
    print(f"连接数据库: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    try:
        cols = get_columns(conn, "group_messages")
        print(f"当前列: {sorted(cols)}\n")

        # ── 1. 新增列（幂等，已存在则跳过）──
        new_cols = {
            "platform":    "VARCHAR(32)  NOT NULL DEFAULT 'wechat'",
            "sender_id":   "VARCHAR(128) NOT NULL DEFAULT ''",
            "sender_name": "VARCHAR(128) NOT NULL DEFAULT ''",
            "chat_name":   "VARCHAR(128) NOT NULL DEFAULT ''",
        }
        for col, typedef in new_cols.items():
            if col in cols:
                print(f"[SKIP] 列已存在: {col}")
            else:
                conn.execute(f"ALTER TABLE group_messages ADD COLUMN {col} {typedef}")
                print(f"[OK]   新增列: {col}")
        conn.commit()

        # ── 2. 回填 sender_id / sender_name（依赖旧 sender 列）──
        cols = get_columns(conn, "group_messages")   # 重新读
        if "sender" in cols:
            cur = conn.execute("SELECT COUNT(*) FROM group_messages WHERE sender_id = ''")
            empty_count = cur.fetchone()[0]
            print(f"\n需要回填的行数: {empty_count}")

            if empty_count > 0:
                conn.execute("UPDATE group_messages SET sender_id   = sender   WHERE sender_id   = ''")
                conn.execute("UPDATE group_messages SET sender_name = sender   WHERE sender_name = ''")
                conn.commit()
                print("[OK]   回填 sender_id / sender_name 完成")

            conn.execute("UPDATE group_messages SET chat_name = chat_id WHERE chat_name = ''")
            conn.commit()
            print("[OK]   回填 chat_name 完成")

            # 验证
            cur = conn.execute("SELECT COUNT(*) FROM group_messages WHERE sender_id = ''")
            remaining = cur.fetchone()[0]
            if remaining > 0:
                print(f"[WARN] 仍有 {remaining} 行 sender_id 为空，请检查！终止 DROP COLUMN")
                sys.exit(1)

            # ── 3. 删除旧 sender 列（SQLite 3.35+）──
            try:
                conn.execute("ALTER TABLE group_messages DROP COLUMN sender")
                conn.commit()
                print("[OK]   删除旧列 sender")
            except Exception as e:
                print(f"[WARN] DROP COLUMN sender 失败（可能版本太旧，手动处理）: {e}")
        else:
            print("[SKIP] 旧列 sender 不存在，跳过回填和删列")

        # ── 4. 创建索引（幂等）──
        indexes = get_indexes(conn, "group_messages")
        if "idx_platform_chat" not in indexes:
            conn.execute("CREATE INDEX idx_platform_chat ON group_messages (platform, chat_id)")
            conn.commit()
            print("[OK]   创建索引 idx_platform_chat")
        else:
            print("[SKIP] 索引 idx_platform_chat 已存在")

        # ── 5. 最终确认 ──
        final_cols = get_columns(conn, "group_messages")
        print(f"\n迁移完成！最终列: {sorted(final_cols)}")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] 迁移失败: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    run()
