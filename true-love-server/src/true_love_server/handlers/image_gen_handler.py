# -*- coding: utf-8 -*-
"""
Image Generation Handler - 图片生成处理器

处理 "生成图片/生成照片" 开头的命令。
"""

import logging
from typing import Optional

from .base_handler import BaseHandler
from .registry import register_handler
from ..models import ChatMsg
from ..services import ImageService

LOG = logging.getLogger("ImageGenHandler")


@register_handler
class ImageGenHandler(BaseHandler):
    """图片生成处理器"""
    
    name = "ImageGenHandler"
    priority = 50  # 中等优先级
    
    def __init__(self):
        self.image_service = ImageService()
    
    def can_handle(self, msg: ChatMsg, cleaned_content: str) -> bool:
        return cleaned_content.startswith('生成') and ('片' in cleaned_content or '图' in cleaned_content)
    
    def handle(self, msg: ChatMsg, cleaned_content: str) -> Optional[str]:
        LOG.info("收到: %s, 生成图片: %s", msg.sender, cleaned_content)
        context_id = msg.chat_id if msg.from_group() else msg.sender
        self.image_service.async_generate(cleaned_content, context_id, msg.sender)
        return None  # 异步处理，无需同步返回
