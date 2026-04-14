# -*- coding: utf-8 -*-
"""
用户记忆数据访问层
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert

from ..models.user_memory import UserMemory

LOG = logging.getLogger("UserMemoryRepository")

# key 白名单，防止 LLM 乱写分类
ALLOWED_KEYS = {"personality", "occupation", "preference", "fact"}


class UserMemoryRepository:
    """用户记忆仓储"""

    def __init__(self, session: Session):
        self.session = session

    def upsert(self, group_id: str, sender: str, key: str, value: str, source: str = None) -> bool:
        """
        插入或更新一条记忆（同 group_id+sender+key 唯一）

        Args:
            group_id: 群 ID（私聊时传 sender）
            sender: 发送者昵称
            key: 记忆分类（personality/occupation/preference/fact）
            value: 记忆内容
            source: 来源（analyze_speech/manual）

        Returns:
            是否成功
        """
        if key not in ALLOWED_KEYS:
            LOG.warning("非法 memory key, 已忽略: %s", key)
            return False

        try:
            stmt = insert(UserMemory).values(
                group_id=group_id,
                sender=sender,
                key=key,
                value=value,
                source=source,
                updated_at=datetime.now(),
            ).on_conflict_do_update(
                index_elements=['group_id', 'sender', 'key'],
                set_={"value": value, "source": source, "updated_at": datetime.now()},
            )
            self.session.execute(stmt)
            self.session.commit()
            LOG.info("upsert memory: group=%s sender=%s key=%s", group_id, sender, key)
            return True
        except Exception as e:
            self.session.rollback()
            LOG.error("upsert memory 失败: %s", e)
            return False

    def get_by_user(self, group_id: str, sender: str) -> list[dict]:
        """
        获取某人在某群的所有记忆条目

        Args:
            group_id: 群 ID
            sender: 发送者

        Returns:
            记忆列表 [{key, value, source, updated_at}]
        """
        try:
            rows = (
                self.session.query(UserMemory)
                .filter(UserMemory.group_id == group_id, UserMemory.sender == sender)
                .order_by(UserMemory.updated_at.desc())
                .all()
            )
            return [
                {
                    "key": r.key,
                    "value": r.value,
                    "source": r.source,
                    "updated_at": r.updated_at.strftime("%Y-%m-%d") if r.updated_at else None,
                }
                for r in rows
            ]
        except Exception as e:
            LOG.error("get_by_user 失败: group=%s sender=%s err=%s", group_id, sender, e)
            return []

    def delete_by_user(self, group_id: str, sender: str) -> int:
        """清除某人在某群的所有记忆，返回删除条数"""
        try:
            count = (
                self.session.query(UserMemory)
                .filter(UserMemory.group_id == group_id, UserMemory.sender == sender)
                .delete()
            )
            self.session.commit()
            return count
        except Exception as e:
            self.session.rollback()
            LOG.error("delete_by_user 失败: %s", e)
            return 0
