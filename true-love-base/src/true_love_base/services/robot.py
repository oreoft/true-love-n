# -*- coding: utf-8 -*-
"""
Robot - 消息处理机器人

负责消息监听、处理和转发。
使用抽象的 WeChatClientProtocol 接口，与底层SDK解耦。
支持异步消息处理，按 chat_id 分组保证同一聊天的消息顺序。
"""

import logging
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, TYPE_CHECKING

from true_love_base.core.client_protocol import WeChatClientProtocol
from true_love_base.models.message import ChatMessage
from true_love_base.services import server_client

if TYPE_CHECKING:
    from true_love_base.services.listen_store import ListenStore


class Robot:
    """
    消息处理机器人
    
    负责:
    - 消息监听和分发
    - 异步消息处理（按 chat_id 分组保证顺序）
    - 消息发送
    """

    # 线程池配置
    MAX_WORKERS = 10

    def __init__(self, client: WeChatClientProtocol, listen_store: "ListenStore") -> None:
        """
        初始化机器人
        
        Args:
            client: 微信客户端实例（实现 WeChatClientProtocol）
            listen_store: 监听列表持久化管理器
        """
        self.client = client
        self.LOG = logging.getLogger("Robot")
        self.self_name = self.client.get_self_name()
        self._listen_store = listen_store

        # 消息处理线程池
        self._executor = ThreadPoolExecutor(
            max_workers=self.MAX_WORKERS,
            thread_name_prefix="MsgHandler"
        )

        # 每个 chat_id 一个锁，保证同一聊天内消息顺序
        self._chat_locks: dict[str, threading.Lock] = defaultdict(threading.Lock)

        self.LOG.info(f"Robot initialized, self_name: {self.self_name}, max_workers: {self.MAX_WORKERS}")

    def forward_msg(self, msg: ChatMessage) -> str:
        """
        转发消息到服务端处理
        
        Args:
            msg: 消息对象
            
        Returns:
            服务端返回的回复内容
        """
        return server_client.get_chat(msg)

    def on_message(self, msg: ChatMessage, chat_name: str) -> None:
        """
        消息回调处理 - 提交到线程池异步处理
        
        Args:
            msg: 收到的消息
            chat_name: 聊天对象名称
        """
        try:
            self.LOG.info(f"Received message from [{chat_name}], submitting to thread pool")
            # 提交到线程池异步处理
            self._executor.submit(self._process_message, msg, chat_name)
        except Exception as e:
            self.LOG.error(f"Error submitting message to thread pool: {e}")

    def _process_message(self, msg: ChatMessage, chat_name: str) -> None:
        """
        实际处理消息 - 在线程池中执行
        
        同一 chat_name 的消息会串行处理，保证顺序。
        不同 chat_name 的消息可以并行处理。
        
        Args:
            msg: 收到的消息
            chat_name: 聊天对象名称
        """
        # 获取该聊天的锁，保证同一 chat_name 的消息顺序
        with self._chat_locks[chat_name]:
            try:
                self.LOG.info(f"Processing message from [{chat_name}]: {msg}")

                # 群消息处理
                if msg.is_group:
                    self.LOG.info(f"Group message, is_at_me={msg.is_at_me}")
                    # 没有艾特自己不处理
                    if not msg.is_at_me:
                        return

                # 转发处理
                self.send_text_msg(self.forward_msg(msg), chat_name, msg.sender if not msg.is_group else None)

            except Exception as e:
                self.LOG.error(f"Error processing message from [{chat_name}]: {e}")

    # 监听添加重试配置
    LISTEN_ADD_RETRY_COUNT = 3
    LISTEN_ADD_RETRY_DELAY = 1.0  # 秒

    def add_listen_chat(self, chat_name: str, persist: bool = True, retry: bool = True) -> bool:
        """
        添加监听的聊天对象
        
        Args:
            chat_name: 聊天对象名称（好友昵称或群名）
            persist: 是否持久化到文件（默认 True）
            retry: 是否在失败时重试（默认 True）
            
        Returns:
            是否添加成功
        """
        import time
        
        max_attempts = self.LISTEN_ADD_RETRY_COUNT if retry else 1
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                success = self.client.add_message_listener(chat_name, self.on_message)
                if success:
                    self.LOG.info(f"Started listening to [{chat_name}] (attempt {attempt})")
                    # 持久化到文件
                    if persist:
                        self._listen_store.add(chat_name)
                    return True
                else:
                    self.LOG.warning(f"Failed to add listener for [{chat_name}] (attempt {attempt}/{max_attempts})")
            except Exception as e:
                last_error = e
                self.LOG.warning(f"Exception adding listener for [{chat_name}] (attempt {attempt}/{max_attempts}): {e}")

            # 如果不是最后一次尝试，等待后重试
            if attempt < max_attempts:
                time.sleep(self.LISTEN_ADD_RETRY_DELAY)

        self.LOG.error(
            f"Failed to add listener for [{chat_name}] after {max_attempts} attempts. Last error: {last_error}")
        return False

    def remove_listen_chat(self, chat_name: str) -> bool:
        """
        移除监听的聊天对象
        
        Args:
            chat_name: 聊天对象名称
            
        Returns:
            是否移除成功
        """
        # 尝试从 SDK 移除监听
        success = self.client.remove_message_listener(chat_name)
        # 无论是否成功，都从持久化中删除
        self._listen_store.remove(chat_name)
        if success:
            self.LOG.info(f"Stopped listening to [{chat_name}]")
        return success

    def get_listen_chats(self) -> list[str]:
        """
        获取所有监听对象（从 DB）
        
        Returns:
            监听对象名称列表
        """
        return self._listen_store.load()

    def load_listen_chats(self) -> dict[str, list[str]]:
        """
        从持久化文件加载监听列表并开始监听
        
        Returns:
            包含成功和失败列表的字典:
            - success: 成功监听的聊天列表
            - failed: 监听失败的聊天列表
        """
        chats = self._listen_store.load()
        self.LOG.info(f"Loading {len(chats)} listen chats from store")
        
        success = []
        failed = []
        
        for chat_name in chats:
            # persist=False 避免重复写入
            if self.add_listen_chat(chat_name, persist=False):
                success.append(chat_name)
            else:
                failed.append(chat_name)
        
        return {"success": success, "failed": failed}

    def refresh_listen_chats(self) -> dict:
        """
        智能刷新监听列表（以 DB 为基准，结合健康检测）
        
        流程：
        1. 从 DB 获取配置的监听列表
        2. 执行健康检测（ChatInfo 响应检测）
        3. 分类处理：
           - healthy: 不处理（skip）
           - unhealthy: 执行 reset
        
        Returns:
            刷新结果，包含:
            - total: 总监听数
            - success_count: 成功数
            - fail_count: 失败数
            - listeners: 每个监听的详情列表
              - chat: 聊天名称
              - before: 刷新前状态 (healthy/unhealthy)
              - action: 执行的操作 (skip/reset)
              - after: 刷新后状态
              - success: 是否成功
        """
        # 获取 DB 配置
        db_chats = self._listen_store.load()
        
        if not db_chats:
            return {
                "total": 0,
                "success_count": 0,
                "fail_count": 0,
                "listeners": []
            }
        
        # 执行健康检测
        status = self.get_listener_status()
        
        self.LOG.info(f"Refresh: DB has {len(db_chats)} chats, status: {status.get('summary', {})}")
        
        listeners = []
        success_count = 0
        fail_count = 0
        
        # 根据状态分类处理（只有 healthy 和 unhealthy 两种状态）
        for item in status.get("listeners", []):
            chat_name = item.get("chat")
            before_status = item.get("status")
            
            listener_info = {
                "chat": chat_name,
                "before": before_status,
                "action": None,
                "after": None,
                "success": None
            }
            
            if before_status == "healthy":
                # 健康的不处理
                listener_info["action"] = "skip"
                listener_info["after"] = "healthy"
                listener_info["success"] = True
                success_count += 1
            else:
                # unhealthy: 执行 reset（包括窗口不存在、ChatInfo 无响应等情况）
                listener_info["action"] = "reset"
                result = self.reset_listener(chat_name)
                success = result.get("success", False)
                listener_info["success"] = success
                if success:
                    listener_info["after"] = "healthy"
                    success_count += 1
                    self.LOG.info(f"Reset listener for [{chat_name}]")
                else:
                    listener_info["after"] = "unhealthy"
                    fail_count += 1
                    self.LOG.error(f"Failed to reset listener for [{chat_name}]: {result.get('message')}")
            
            listeners.append(listener_info)
        
        return {
            "total": len(listeners),
            "success_count": success_count,
            "fail_count": fail_count,
            "listeners": listeners
        }

    def start_listening(self) -> None:
        """
        开始消息监听（阻塞）
        
        注意：这个方法会阻塞当前线程
        """
        self.LOG.info("Robot starting to listen...")
        self.client.start_listening()

    def cleanup(self) -> None:
        """
        清理资源
        
        关闭线程池，等待所有任务完成。
        """
        self.LOG.info("Robot cleanup: shutting down thread pool...")
        self._executor.shutdown(wait=True, cancel_futures=False)
        self.LOG.info("Robot cleanup: thread pool shutdown complete")

    # ==================== 消息发送 ====================

    def send_text_msg(self, msg: str, receiver: str, at_user: Optional[str] = None) -> bool:
        """
        发送文本消息
        
        Args:
            msg: 消息内容
            receiver: 接收者
            at_user: 要@的用户（可选）
            
        Returns:
            是否发送成功
        """
        if not msg or not msg.strip():
            return False

        at_list = [at_user] if at_user else None
        self.LOG.info(f"Sending to [{receiver}]: {msg[:50]}...")
        return self.client.send_text(receiver, msg, at_list)

    def send_img_msg(self, path: str, receiver: str) -> bool:
        """
        发送图片消息
        
        Args:
            path: 图片路径
            receiver: 接收者
            
        Returns:
            是否发送成功
        """
        self.LOG.info(f"Sending image to [{receiver}]: {path}")
        return self.client.send_image(receiver, path)

    def send_file_msg(self, path: str, receiver: str) -> bool:
        """
        发送文件
        
        Args:
            path: 文件路径
            receiver: 接收者
            
        Returns:
            是否发送成功
        """
        self.LOG.info(f"Sending file to [{receiver}]: {path}")
        return self.client.send_file(receiver, path)

    # ==================== 联系人 ====================

    def get_all_contacts(self) -> dict[str, str]:
        """
        获取所有联系人
        
        Returns:
            联系人字典 {id: nickname}
        """
        return self.client.get_contacts()

    def get_contacts_by_chat_name(self, chat_name: str) -> dict[str, str]:
        """
        获取群成员
        
        Args:
            chat_name: 群名称
            
        Returns:
            群成员字典 {id: nickname}
        """
        return self.client.get_chat_members(chat_name)

    # ==================== 监听状态与恢复 ====================

    def get_listener_status(self) -> dict:
        """
        获取监听状态（以 DB 为基准，ChatInfo 响应为健康金标准）
        
        状态定义（只有两种）：
        - healthy: 子窗口存在 AND ChatInfo 能正确响应
        - unhealthy: 子窗口不存在 OR ChatInfo 无法响应
            
        Returns:
            状态结果字典，包含:
            - listeners: 每个监听的状态列表
              - chat: 聊天名称
              - status: healthy / unhealthy
              - reason: 不健康的原因（可选）
            - summary: 状态汇总 {"healthy": N, "unhealthy": M}
        """
        # 从 DB 获取配置的监听列表
        db_chats = self._listen_store.load()
        return self.client.get_listener_status(db_chats)

    def reset_listener(self, chat_name: str) -> dict:
        """
        重置指定聊天的监听（基于 DB）
        
        Args:
            chat_name: 聊天对象名称
            
        Returns:
            重置结果字典
        """
        # 检查 DB 中是否有该配置
        if not self._listen_store.exists(chat_name):
            return {
                "success": False,
                "message": f"Chat [{chat_name}] not found in DB config"
            }
        
        # 调用 client 重置，传入统一的回调
        return self.client.reset_listener(chat_name, self.on_message)

    def reset_all_listeners(self) -> dict:
        """
        重置所有监听（基于 DB）
        
        Returns:
            重置结果字典
        """
        # 从 DB 获取配置的监听列表
        db_chats = self._listen_store.load()
        
        if not db_chats:
            return {
                "success": True,
                "message": "No listeners in DB config",
                "total": 0,
                "recovered": [],
                "failed": []
            }
        
        # 调用 client 重置，传入 chat_list 和统一的回调
        return self.client.reset_all_listeners(db_chats, self.on_message)
