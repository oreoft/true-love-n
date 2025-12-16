# -*- coding: utf-8 -*-
"""
Message Router - 消息路由

根据消息类型和来源分发到对应的处理器。

注意：响应白名单判断已移到 base 端（通过 listen_chats 配置）
base 只会发送需要处理的消息到 server
"""

from models.chat_msg import ChatMsg
from msg_handler import MsgHandler

msg_handler = MsgHandler()


def router_msg(msg: ChatMsg) -> str:
    """
    消息路由
    
    注意：base 端已经过滤了不需要处理的消息，这里直接处理即可。
    - 群消息：base 端已判断是否被@
    - 私聊消息：base 端已判断是否在监听列表
    
    Args:
        msg: 聊天消息
        
    Returns:
        回复内容
    """
    return msg_handler.handler_msg(msg)
