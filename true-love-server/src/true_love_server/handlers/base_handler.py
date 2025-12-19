# -*- coding: utf-8 -*-
"""
Base Handler - 处理器基类

定义消息处理器的接口规范。
"""

from abc import ABC, abstractmethod
from typing import Optional

from ..models import ChatMsg


class BaseHandler(ABC):
    """
    消息处理器基类
    
    所有消息处理器都应继承此类并实现相应方法。
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """处理器名称，用于日志和调试"""
        pass
    
    @property
    def priority(self) -> int:
        """
        优先级，数字越小优先级越高
        
        默认 100，可被子类覆盖。
        特殊命令（如 $查询）应设置较高优先级（较小数字）。
        """
        return 100
    
    @abstractmethod
    def can_handle(self, msg: ChatMsg, cleaned_content: str) -> bool:
        """
        判断是否能处理该消息
        
        Args:
            msg: 原始消息对象
            cleaned_content: 清理后的消息内容（已移除 @真爱粉 等前缀）
            
        Returns:
            bool: 是否能处理
        """
        pass
    
    @abstractmethod
    def handle(self, msg: ChatMsg, cleaned_content: str) -> Optional[str]:
        """
        处理消息
        
        Args:
            msg: 原始消息对象
            cleaned_content: 清理后的消息内容
            
        Returns:
            Optional[str]: 回复内容，None 表示异步处理或无需回复
        """
        pass
