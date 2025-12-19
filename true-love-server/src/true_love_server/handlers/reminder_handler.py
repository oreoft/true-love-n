# -*- coding: utf-8 -*-
"""
Reminder Handler - 提醒处理器

处理 $提醒 开头的命令。
"""

import logging
from typing import Optional

from .base_handler import BaseHandler
from .registry import register_handler
from .trig_remainder_handler import TrigRemainderHandler
from ..models import ChatMsg

LOG = logging.getLogger("ReminderHandler")


@register_handler
class ReminderHandler(BaseHandler):
    """提醒处理器"""
    
    name = "ReminderHandler"
    priority = 10  # 高优先级
    
    def __init__(self):
        self.reminder_handler = TrigRemainderHandler()
    
    def can_handle(self, msg: ChatMsg, cleaned_content: str) -> bool:
        return cleaned_content.startswith('$提醒')
    
    def handle(self, msg: ChatMsg, cleaned_content: str) -> Optional[str]:
        LOG.info("收到: %s, 提醒任务: %s", msg.sender, cleaned_content)
        target = msg.chat_id if msg.from_group() else msg.sender
        return self.reminder_handler.router(cleaned_content, target, msg.sender)
