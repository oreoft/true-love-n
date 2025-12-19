# -*- coding: utf-8 -*-
"""
Admin Handler - 管理处理器

处理 $管理 开头的命令。
"""

import logging
from typing import Optional

from .base_handler import BaseHandler
from .registry import register_handler
from .trig_manage_handler import TrigManageHandler
from ..models import ChatMsg

LOG = logging.getLogger("AdminHandler")


@register_handler
class AdminHandler(BaseHandler):
    """管理处理器"""
    
    name = "AdminHandler"
    priority = 10  # 高优先级
    
    def __init__(self):
        self.manage_handler = TrigManageHandler()
    
    def can_handle(self, msg: ChatMsg, cleaned_content: str) -> bool:
        return cleaned_content.startswith('$管理')
    
    def handle(self, msg: ChatMsg, cleaned_content: str) -> Optional[str]:
        LOG.info("收到: %s, 管理任务: %s", msg.sender, cleaned_content)
        return self.manage_handler.run(cleaned_content, msg.sender)
