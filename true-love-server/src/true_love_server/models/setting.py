# -*- coding: utf-8 -*-
"""
Setting 模型

后台可改的设置，一行一项，由 create_all() 统一建表。
"""

from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime

from .group_message import Base


class Setting(Base):
    """设置表"""

    __tablename__ = "settings"

    key        = Column(String(64), primary_key=True, comment="设置项")
    value      = Column(Text,       nullable=False,   comment="设置值（JSON）")
    updated_at = Column(DateTime,   nullable=False, default=datetime.now, comment="最后修改时间")
