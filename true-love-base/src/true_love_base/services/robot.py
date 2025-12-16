# -*- coding: utf-8 -*-
"""
Robot - 消息处理机器人

负责消息监听、处理和转发。
使用抽象的 WeChatClientProtocol 接口，与底层SDK解耦。
"""

import logging
from typing import Optional

from true_love_base.core.client_protocol import WeChatClientProtocol
from true_love_base.models.message import (
    BaseMessage,
    TextMessage,
    ImageMessage,
    VoiceMessage,
    VideoMessage,
    MessageType,
)
from true_love_base.services import server_client


class Robot:
    """
    消息处理机器人
    
    负责:
    - 消息监听和分发
    - 消息处理逻辑
    - 消息发送
    """
    
    def __init__(self, client: WeChatClientProtocol) -> None:
        """
        初始化机器人
        
        Args:
            client: 微信客户端实例（实现 WeChatClientProtocol）
        """
        self.client = client
        self.LOG = logging.getLogger("Robot")
        self.self_name = self.client.get_self_name()
        self._listening_chats: set[str] = set()
        
        self.LOG.info(f"Robot initialized, self_name: {self.self_name}")
    
    def forward_msg(self, msg: BaseMessage) -> str:
        """
        转发消息到服务端处理
        
        Args:
            msg: 消息对象
            
        Returns:
            服务端返回的回复内容
        """
        return server_client.get_chat(msg)
    
    def on_message(self, msg: BaseMessage, chat_name: str) -> None:
        """
        消息回调处理
        
        Args:
            msg: 收到的消息
            chat_name: 聊天对象名称
        """
        try:
            self.LOG.info(f"Received message from [{chat_name}]: {msg}")
            
            # 过滤微信系统消息
            if 'weixin' in msg.sender.lower() or msg.sender == 'system':
                self.LOG.debug(f"Ignored system message from [{msg.sender}]")
                return
            
            # 过滤自己发送的消息
            if msg.is_self:
                return
            
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
            self.LOG.error(f"Error processing message: {e}")
    
    def add_listen_chat(self, chat_name: str, is_group: bool = False) -> bool:
        """
        添加监听的聊天对象
        
        Args:
            chat_name: 聊天对象名称（好友昵称或群名）
            is_group: 是否群聊
            
        Returns:
            是否添加成功
        """
        if chat_name in self._listening_chats:
            self.LOG.warning(f"Already listening to [{chat_name}]")
            return True
        
        success = self.client.add_message_listener(chat_name, self.on_message, is_group)
        if success:
            self._listening_chats.add(chat_name)
            self.LOG.info(f"Started listening to [{chat_name}], is_group={is_group}")
        return success
    
    def remove_listen_chat(self, chat_name: str) -> bool:
        """
        移除监听的聊天对象
        
        Args:
            chat_name: 聊天对象名称
            
        Returns:
            是否移除成功
        """
        if chat_name not in self._listening_chats:
            return True
        
        success = self.client.remove_message_listener(chat_name)
        if success:
            self._listening_chats.discard(chat_name)
            self.LOG.info(f"Stopped listening to [{chat_name}]")
        return success
    
    def start_listening(self) -> None:
        """
        开始消息监听（阻塞）
        
        注意：这个方法会阻塞当前线程
        """
        self.LOG.info("Robot starting to listen...")
        self.client.start_listening()
    
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
