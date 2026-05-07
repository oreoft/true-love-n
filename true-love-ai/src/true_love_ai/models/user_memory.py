# -*- coding: utf-8 -*-
"""
用户画像记忆模型

存储用户的长期记忆（性格、职业、爱好等）。
每个群是信息孤岛，同一个人在不同群有独立画像。
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Index, Text

from true_love_ai.core.db_engine import Base


class UserMemory(Base):
    """用户画像表"""

    __tablename__ = 'user_memory'

    id = Column(Integer, primary_key=True, autoincrement=True)

    group_id = Column(String(128), nullable=False, comment="群聊ID（私聊时等于sender）")
    sender_id = Column(String(128), nullable=False, comment="发送者唯一 ID")

    key = Column(String(64), nullable=False, comment="格式: category.sub_key（如 interest.music）或特殊key（timezone）")
    value = Column(Text, nullable=False, comment="记忆内容")
    source = Column(String(32), nullable=True, comment="来源: analyze_speech/manual/skill")

    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index('idx_user_memory_unique', 'group_id', 'sender_id', 'key', unique=True),
        Index('idx_user_memory_lookup', 'group_id', 'sender_id'),
    )

    def __repr__(self):
        return f"<UserMemory(group={self.group_id}, sender_id={self.sender_id}, key={self.key})>"
