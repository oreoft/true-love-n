# -*- coding: utf-8 -*-
"""
Handler Registry - 处理器注册表

管理所有消息处理器的注册和查找。
"""

import logging
from typing import List, Optional, Type

from .base_handler import BaseHandler
from ..models import ChatMsg

LOG = logging.getLogger("HandlerRegistry")


class HandlerRegistry:
    """
    处理器注册表
    
    管理所有消息处理器，按优先级排序。
    """
    
    def __init__(self):
        self._handlers: List[BaseHandler] = []
        self._sorted = False
    
    def register(self, handler: BaseHandler) -> BaseHandler:
        """
        注册处理器
        
        Args:
            handler: 处理器实例
            
        Returns:
            handler: 返回处理器本身（便于链式调用）
        """
        self._handlers.append(handler)
        self._sorted = False
        LOG.info("注册处理器: %s (priority=%d)", handler.name, handler.priority)
        return handler
    
    def _ensure_sorted(self):
        """确保处理器按优先级排序"""
        if not self._sorted:
            self._handlers.sort(key=lambda h: h.priority)
            self._sorted = True
    
    def get_handler(self, msg: ChatMsg, cleaned_content: str) -> Optional[BaseHandler]:
        """
        获取能处理消息的处理器
        
        Args:
            msg: 消息对象
            cleaned_content: 清理后的消息内容
            
        Returns:
            能处理的处理器，找不到返回 None
        """
        self._ensure_sorted()
        
        for handler in self._handlers:
            if handler.can_handle(msg, cleaned_content):
                LOG.debug("消息由 %s 处理", handler.name)
                return handler
        
        return None
    
    def get_all_handlers(self) -> List[BaseHandler]:
        """获取所有处理器（按优先级排序）"""
        self._ensure_sorted()
        return list(self._handlers)
    
    def clear(self):
        """清空所有处理器（主要用于测试）"""
        self._handlers.clear()
        self._sorted = False


# 全局注册表实例
registry = HandlerRegistry()


def register_handler(cls: Type[BaseHandler]) -> Type[BaseHandler]:
    """
    处理器注册装饰器
    
    用法:
        @register_handler
        class MyHandler(BaseHandler):
            ...
    """
    registry.register(cls())
    return cls
