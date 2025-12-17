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
        self._listening_chats: set[str] = set()
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
            # 快速过滤，不需要进入线程池
            if 'weixin' in msg.sender.lower() or msg.sender == 'system':
                self.LOG.debug(f"Ignored system message from [{msg.sender}]")
                return
            
            if msg.is_self:
                return
            
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
                    # 只处理@了自己的消息
                    if msg.is_at_me:
                        reply = self.forward_msg(msg)
                        self.send_text_msg(reply, chat_name, msg.sender)
                    return
                
                # 私聊消息，全部转发处理
                reply = self.forward_msg(msg)
                self.send_text_msg(reply, chat_name)
                
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
        
        if chat_name in self._listening_chats:
            self.LOG.warning(f"Already listening to [{chat_name}]")
            return True
        
        max_attempts = self.LISTEN_ADD_RETRY_COUNT if retry else 1
        last_error = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                success = self.client.add_message_listener(chat_name, self.on_message)
                if success:
                    self._listening_chats.add(chat_name)
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
        
        self.LOG.error(f"Failed to add listener for [{chat_name}] after {max_attempts} attempts. Last error: {last_error}")
        return False
    
    def remove_listen_chat(self, chat_name: str) -> bool:
        """
        移除监听的聊天对象
        
        Args:
            chat_name: 聊天对象名称
            
        Returns:
            是否移除成功
        """
        if chat_name not in self._listening_chats:
            # 即使内存中没有，也尝试从持久化中删除
            self._listen_store.remove(chat_name)
            return True
        
        success = self.client.remove_message_listener(chat_name)
        if success:
            self._listening_chats.discard(chat_name)
            self._listen_store.remove(chat_name)
            self.LOG.info(f"Stopped listening to [{chat_name}]")
        return success
    
    def get_listen_chats(self) -> list[str]:
        """
        获取所有监听对象
        
        Returns:
            监听对象名称列表
        """
        return list(self._listening_chats)
    
    def load_listen_chats(self) -> None:
        """从持久化文件加载监听列表并开始监听"""
        chats = self._listen_store.load()
        self.LOG.info(f"Loading {len(chats)} listen chats from store")
        for chat_name in chats:
            # persist=False 避免重复写入
            self.add_listen_chat(chat_name, persist=False)
    
    def refresh_listen_chats(self) -> dict:
        """
        刷新监听列表：比对内存和文件，重新添加缺失的监听
        
        Returns:
            刷新结果，包含:
            - file_chats: 文件中的监听列表
            - memory_chats: 内存中的监听列表
            - missing: 文件中有但内存中没有的
            - extra: 内存中有但文件中没有的
            - recovered: 成功恢复的
            - failed: 恢复失败的
        """
        # 获取文件中的监听列表
        file_chats = set(self._listen_store.load())
        # 获取内存中的监听列表
        memory_chats = set(self._listening_chats)
        
        # 计算差异
        missing = file_chats - memory_chats  # 文件有，内存没有
        extra = memory_chats - file_chats    # 内存有，文件没有
        
        self.LOG.info(f"Refresh: file={len(file_chats)}, memory={len(memory_chats)}, missing={len(missing)}, extra={len(extra)}")
        
        recovered = []
        failed = []
        
        # 尝试恢复缺失的监听
        for chat_name in missing:
            self.LOG.info(f"Attempting to recover listener for [{chat_name}]")
            # persist=False 因为文件中已经有了
            success = self.add_listen_chat(chat_name, persist=False, retry=True)
            if success:
                recovered.append(chat_name)
                self.LOG.info(f"Successfully recovered listener for [{chat_name}]")
            else:
                failed.append(chat_name)
                self.LOG.error(f"Failed to recover listener for [{chat_name}]")
        
        return {
            "file_chats": list(file_chats),
            "memory_chats": list(self._listening_chats),  # 更新后的内存列表
            "missing": list(missing),
            "extra": list(extra),
            "recovered": recovered,
            "failed": failed,
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
