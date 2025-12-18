# -*- coding: utf-8 -*-
"""
WeChat Client Protocol - 微信客户端抽象协议

定义微信客户端的抽象接口，所有具体实现（如 wxautox4, wcferry 等）
都应该实现这个协议。这样可以实现底层SDK的无缝切换。
"""

from abc import ABC, abstractmethod
from typing import Callable, Optional, Any
from true_love_base.models.message import ChatMessage


# 消息回调函数类型定义
# callback(message: ChatMessage, chat_name: str) -> None
MessageCallback = Callable[[ChatMessage, str], None]


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
    def add_message_listener(self, chat_name: str, callback: MessageCallback) -> bool:
        """
        添加消息监听器
        
        Args:
            chat_name: 要监听的聊天对象（好友昵称或群名）
            callback: 消息回调函数
            
        Returns:
            是否添加成功
            
        Note:
            是否群聊由适配器在运行时推断
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

    @abstractmethod
    def is_listening(self, chat_name: str) -> bool:
        """
        检查是否正在监听某个聊天（以运行时状态为准）
        
        Args:
            chat_name: 聊天对象名称
            
        Returns:
            是否正在监听
        """
        pass

    # ==================== 监听状态与恢复 ====================

    @abstractmethod
    def get_listener_status(self, db_chats: list[str], probe: bool = False) -> dict:
        """
        获取监听状态（以 DB 为基准）
        
        Args:
            db_chats: DB 中配置的监听列表（基准值）
            probe: 是否执行主动探测（ChatInfo 检测）
            
        Returns:
            状态结果字典，包含:
            - listeners: 每个监听的状态列表
              - chat: 聊天名称
              - status: not_listening / listening / healthy / unhealthy
              - reason: 失败原因（可选）
            - summary: 状态汇总
            - probe_mode: 是否为探测模式
        """
        pass

    @abstractmethod
    def reset_listener(self, chat_name: str, callback: MessageCallback) -> dict:
        """
        重置指定聊天的监听
        
        通过关闭子窗口、移除监听、重新添加监听的方式恢复异常的监听。
        不依赖内存状态，使用传入的 callback 参数。
        
        Args:
            chat_name: 聊天对象名称
            callback: 消息回调函数
            
        Returns:
            重置结果字典，包含:
            - success: 是否成功
            - message: 结果描述
            - steps: 各步骤执行情况
        """
        pass

    @abstractmethod
    def reset_all_listeners(self, chat_list: list[str], callback: MessageCallback) -> dict:
        """
        重置所有监听
        
        通过停止所有监听、关闭所有子窗口、刷新 UI、重新添加所有监听的方式恢复。
        不依赖内存状态，使用传入的 chat_list 和 callback 参数。
        
        Args:
            chat_list: 要重置的聊天列表（通常来自 DB）
            callback: 消息回调函数
        
        Returns:
            重置结果字典，包含:
            - success: 是否成功
            - message: 结果描述
            - total: 总监听数
            - recovered: 成功恢复的列表
            - failed: 恢复失败的列表
            - steps: 各步骤执行情况
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
