# -*- coding: utf-8 -*-
"""群消息取数 helper（内部使用，不注册为 skill）"""

from true_love_ai.agent.server_client import query_group_history, query_history


async def fetch_group_messages(chat_id: str, limit: int, sender_id: str = "") -> list[dict]:
    """
    统一取群消息入口。

    Args:
        chat_id:   群聊 ID
        limit:     最多返回条数
        sender_id: 非空时只取该发言人的消息
    """
    if sender_id:
        return await query_history(chat_id, sender_id, limit=limit)
    return await query_group_history(chat_id, limit=limit)
