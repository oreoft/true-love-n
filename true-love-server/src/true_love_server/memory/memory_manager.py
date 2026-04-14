# -*- coding: utf-8 -*-
"""
记忆管理器

提供统一的记忆读写入口，屏蔽 DB session 细节。
"""

import logging
from typing import Optional

from ..core.db_engine import SessionLocal
from .user_memory_repository import UserMemoryRepository

LOG = logging.getLogger("MemoryManager")

# key 的中文展示名，用于拼接 user_ctx 字符串
_KEY_LABELS = {
    "personality": "性格",
    "occupation":  "职业",
    "preference":  "爱好/偏好",
    "fact":        "其他信息",
}


def get_user_context(group_id: str, sender: str) -> Optional[str]:
    """
    获取某人在某群的记忆，拼接为纯文本供注入 system prompt。

    返回格式（有记忆时）：
        "职业：程序员 | 性格：外向幽默 | 爱好/偏好：喜欢海贼王"
    无记忆时返回 None。

    Args:
        group_id: 群 ID（私聊时传 sender）
        sender:   发送者昵称
    """
    try:
        with SessionLocal() as db:
            repo = UserMemoryRepository(db)
            memories = repo.get_by_user(group_id, sender)

        if not memories:
            return None

        parts = []
        for m in memories:
            label = _KEY_LABELS.get(m["key"], m["key"])
            parts.append(f"{label}：{m['value']}")

        return " | ".join(parts)
    except Exception as e:
        LOG.error("get_user_context 失败: group=%s sender=%s err=%s", group_id, sender, e)
        return None


def upsert_user_memory(group_id: str, sender: str, facts: list[dict], source: str = "analyze_speech") -> int:
    """
    批量写入用户记忆条目。

    Args:
        group_id: 群 ID
        sender:   发送者昵称
        facts:    [{key, value}, ...] 列表（来自 /extract-memory 接口）
        source:   来源标记

    Returns:
        成功写入的条数
    """
    if not facts:
        return 0

    success_count = 0
    try:
        with SessionLocal() as db:
            repo = UserMemoryRepository(db)
            for fact in facts:
                key = fact.get("key", "").strip()
                value = fact.get("value", "").strip()
                if key and value:
                    if repo.upsert(group_id, sender, key, value, source):
                        success_count += 1
    except Exception as e:
        LOG.error("upsert_user_memory 失败: %s", e)

    LOG.info("写入记忆 %d 条: group=%s sender=%s", success_count, group_id, sender)
    return success_count


def clear_user_memory(group_id: str, sender: str) -> int:
    """清除某人在某群的所有记忆，返回删除条数"""
    try:
        with SessionLocal() as db:
            repo = UserMemoryRepository(db)
            return repo.delete_by_user(group_id, sender)
    except Exception as e:
        LOG.error("clear_user_memory 失败: %s", e)
        return 0
