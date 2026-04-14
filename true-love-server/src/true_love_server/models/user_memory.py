# -*- coding: utf-8 -*-
"""
用户记忆模型

存储群内用户画像，实现跨会话的长期记忆。
每个群是信息孤岛，同一个人在不同群有独立的画像。
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Index, Text
from sqlalchemy.ext.declarative import declarative_base

# 复用 group_message 的 Base，保证注册到同一个 metadata
from .group_message import Base


class UserMemory(Base):
    """群内用户画像表"""

    __tablename__ = 'user_memory'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 信息孤岛边界：group_id + sender 确定一个人在一个群的画像
    group_id = Column(String(128), nullable=False, comment="群聊ID（私聊时等于sender）")
    sender = Column(String(128), nullable=False, comment="发送者昵称")

    # 记忆条目
    key = Column(String(64), nullable=False, comment="分类: personality/occupation/preference/fact")
    value = Column(Text, nullable=False, comment="记忆内容")
    source = Column(String(32), nullable=True, comment="来源: analyze_speech/manual")

    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        # 同一个群同一个人同一个 key 只有一条，upsert 时覆盖
        Index('idx_user_memory_unique', 'group_id', 'sender', 'key', unique=True),
        # 查询索引
        Index('idx_user_memory_lookup', 'group_id', 'sender'),
    )

    def __repr__(self):
        return f"<UserMemory(group={self.group_id}, sender={self.sender}, key={self.key})>"
