# -*- coding: utf-8 -*-
"""
Query Handler - 查询处理器

处理 $查询 开头的命令。
"""

import logging
from typing import Optional

from .base_handler import BaseHandler
from .registry import register_handler
from .trig_search_handler import TrigSearchHandler
from ..models import ChatMsg

LOG = logging.getLogger("QueryHandler")


@register_handler
class QueryHandler(BaseHandler):
    """查询处理器"""
    
    name = "QueryHandler"
    priority = 10  # 高优先级
    
    def __init__(self):
        self.search_handler = TrigSearchHandler()
    
    def can_handle(self, msg: ChatMsg, cleaned_content: str) -> bool:
        return cleaned_content.startswith('$查询')
    
    def handle(self, msg: ChatMsg, cleaned_content: str) -> Optional[str]:
        LOG.info("收到: %s, 查询任务: %s", msg.sender, cleaned_content)
        return self.search_handler.run(cleaned_content)
