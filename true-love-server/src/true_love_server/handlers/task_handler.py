# -*- coding: utf-8 -*-
"""
Task Handler - 任务处理器

处理 $执行 开头的命令。
"""

import logging
from typing import Optional

from .base_handler import BaseHandler
from .registry import register_handler
from .trig_task_handler import TrigTaskHandler
from ..models import ChatMsg

LOG = logging.getLogger("TaskHandler")


@register_handler
class TaskHandler(BaseHandler):
    """任务处理器"""
    
    name = "TaskHandler"
    priority = 10  # 高优先级
    
    def __init__(self):
        self.task_handler = TrigTaskHandler()
    
    def can_handle(self, msg: ChatMsg, cleaned_content: str) -> bool:
        return cleaned_content.startswith('$执行')
    
    def handle(self, msg: ChatMsg, cleaned_content: str) -> Optional[str]:
        LOG.info("收到: %s, 执行任务: %s", msg.sender, cleaned_content)
        return self.task_handler.run(cleaned_content, msg.sender, msg.chat_id)
