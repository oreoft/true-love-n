# -*- coding: utf-8 -*-
"""
Listen Store - 监听列表持久化

监听列表存在这台 server 的数据库里，只有 server 读写；
base 连上微信时通过 /listen/list 接口来取。
"""

import logging

from ..core.db_engine import SessionLocal
from ..models.listen_chat import ListenChat

LOG = logging.getLogger("ListenStore")


def list_all() -> list[str]:
    """全部监听对象，按加入顺序"""
    with SessionLocal() as db:
        rows = db.query(ListenChat.chat_name).order_by(ListenChat.created_at).all()
        return [row.chat_name for row in rows]


def exists(chat_name: str) -> bool:
    with SessionLocal() as db:
        return db.get(ListenChat, chat_name) is not None


def add(chat_name: str) -> bool:
    """加入监听列表，已存在时返回 False"""
    with SessionLocal() as db:
        if db.get(ListenChat, chat_name) is not None:
            return False
        db.add(ListenChat(chat_name=chat_name))
        db.commit()
    LOG.info("Added [%s] to listen list", chat_name)
    return True


def remove(chat_name: str) -> bool:
    """移出监听列表，不存在时返回 False"""
    with SessionLocal() as db:
        row = db.get(ListenChat, chat_name)
        if row is None:
            return False
        db.delete(row)
        db.commit()
    LOG.info("Removed [%s] from listen list", chat_name)
    return True
