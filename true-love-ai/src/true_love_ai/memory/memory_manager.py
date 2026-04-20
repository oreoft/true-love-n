# -*- coding: utf-8 -*-
"""
记忆管理器

提供统一的用户画像读写入口，供 Agent Loop 和 Skills 使用。
"""

import logging
from typing import Optional

from true_love_ai.core.db_engine import SessionLocal
from true_love_ai.memory.user_memory_repository import UserMemoryRepository

LOG = logging.getLogger("MemoryManager")

_CATEGORY_LABELS = {
    "personality": "性格",
    "occupation":  "职业",
    "preference":  "偏好",
    "fact":        "事实",
    "interest":    "兴趣",
    "habit":       "习惯",
    "personal":    "个人信息",
    "event":       "事件",
    "timezone":    "时区",
}


def _format_key(key: str) -> str:
    """把 category.sub_key 格式的 key 转成可读标签"""
    if "." in key:
        category, sub = key.split(".", 1)
        cat_label = _CATEGORY_LABELS.get(category, category)
        return f"{cat_label}({sub})"
    return _CATEGORY_LABELS.get(key, key)


def get_user_context(group_id: str, sender: str) -> Optional[str]:
    """
    获取某人在某群的画像记忆，拼接为纯文本供注入 system prompt。

    返回格式（有记忆时）：
        "职业：程序员 | 性格：外向幽默 | 兴趣(音乐)：喜欢爵士乐 | 时区：Asia/Shanghai"
    无记忆时返回 None。
    """
    try:
        with SessionLocal() as db:
            repo = UserMemoryRepository(db)
            memories = repo.get_by_user(group_id, sender)

        if not memories:
            return None

        parts = [f"{_format_key(m['key'])}：{m['value']}" for m in memories]
        return " | ".join(parts)
    except Exception as e:
        LOG.error("get_user_context 失败: group=%s sender=%s err=%s", group_id, sender, e)
        return None


def list_user_memory(group_id: str, sender: str) -> list[dict]:
    """返回用户所有记忆条目，供 query_user_memory skill 使用"""
    try:
        with SessionLocal() as db:
            repo = UserMemoryRepository(db)
            return repo.get_by_user(group_id, sender)
    except Exception as e:
        LOG.error("list_user_memory 失败: group=%s sender=%s err=%s", group_id, sender, e)
        return []


def upsert_user_memory(group_id: str, sender: str, facts: list[dict], source: str = "skill") -> int:
    """
    批量写入用户记忆条目。

    Args:
        group_id: 群 ID（私聊时传 sender）
        sender:   发送者昵称
        facts:    [{key, value}, ...] 列表
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
