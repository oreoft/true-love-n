# -*- coding: utf-8 -*-
"""群消息取数 helper（内部使用，不注册为 skill）"""

from true_love_ai.agent.server_client import query_group_history, query_history


async def fetch_group_messages(chat_id: str, limit: int,
                               sender_id: str = "", sender_name: str = "") -> list[dict]:
    """统一取群消息入口，sender_id / sender_name 均为可选过滤条件。"""
    if sender_id or sender_name:
        return await query_history(chat_id, sender_id=sender_id, sender_name=sender_name, limit=limit)
    return await query_group_history(chat_id, limit=limit)
