# -*- coding: utf-8 -*-
"""
WeChat Client Protocol - 微信客户端抽象协议

定义微信客户端的抽象接口，所有具体实现（如 wxautox4, wcferry 等）
都应该实现这个协议。这样可以实现底层SDK的无缝切换。
"""

from abc import ABC, abstractmethod
from typing import Callable, Optional, Any
from models.message import BaseMessage


# 消息回调函数类型定义
# callback(message: BaseMessage, chat_name: str) -> None
MessageCallback = Callable[[BaseMessage, str], None]


class WeChatClientProtocol(ABC):
    """
    微信客户端抽象协议
    
    定义了微信客户端必须实现的核心功能接口。
    所有具体的SDK适配器都应该实现这个协议。
    """

    @abstractmethod
    def get_self_id(self) -> str:
        """
        获取当前登录账号的ID
        
        Returns:
            当前登录用户的wxid或唯一标识
        """
        pass

    @abstractmethod
    def get_self_name(self) -> str:
        """
        获取当前登录账号的昵称
        
        Returns:
            当前登录用户的昵称
        """
        pass

    # ==================== 消息发送 ====================

    @abstractmethod
    def send_text(self, receiver: str, content: str, at_list: Optional[list[str]] = None) -> bool:
        """
        发送文本消息
        
        Args:
            receiver: 接收者（好友昵称或群名）
            content: 消息内容
            at_list: 要@的人列表（仅群聊有效）
            
        Returns:
            是否发送成功
        """
        pass

    @abstractmethod
    def send_image(self, receiver: str, image_path: str) -> bool:
        """
        发送图片消息
        
        Args:
            receiver: 接收者
            image_path: 图片文件路径
            
        Returns:
            是否发送成功
        """
        pass

    @abstractmethod
    def send_file(self, receiver: str, file_path: str) -> bool:
        """
        发送文件
        
        Args:
            receiver: 接收者
            file_path: 文件路径
            
        Returns:
            是否发送成功
        """
        pass

    # ==================== 消息监听 ====================

    @abstractmethod
    def add_message_listener(self, chat_name: str, callback: MessageCallback, is_group: bool = False) -> bool:
        """
        添加消息监听器
        
        Args:
            chat_name: 要监听的聊天对象（好友昵称或群名）
            callback: 消息回调函数
            is_group: 是否群聊
            
        Returns:
            是否添加成功
        """
        pass

    @abstractmethod
    def remove_message_listener(self, chat_name: str) -> bool:
        """
        移除消息监听器
        
        Args:
            chat_name: 聊天对象名称
            
        Returns:
            是否移除成功
        """
        pass

    @abstractmethod
    def start_listening(self) -> None:
        """
        开始消息监听（阻塞式）
        
        这个方法会阻塞当前线程，持续监听消息。
        通常在单独的线程中调用。
        """
        pass

    # ==================== 联系人管理 ====================

    @abstractmethod
    def get_contacts(self) -> dict[str, str]:
        """
        获取所有联系人
        
        Returns:
            联系人字典 {id: nickname}
        """
        pass

    @abstractmethod
    def get_chat_members(self, chat_name: str) -> dict[str, str]:
        """
        获取群成员列表
        
        Args:
            chat_name: 群名称
            
        Returns:
            群成员字典 {id: nickname}
        """
        pass

    # ==================== 生命周期 ====================

    @abstractmethod
    def is_running(self) -> bool:
        """
        检查客户端是否在运行
        
        Returns:
            是否运行中
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """
        清理资源，关闭连接
        """
        pass


