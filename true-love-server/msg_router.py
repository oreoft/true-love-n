# -*- coding: utf-8 -*-
"""
Message Router - 消息路由

根据消息类型和来源分发到对应的处理器。
"""

from configuration import Config
from models.chat_msg import ChatMsg
from msg_handler import MsgHandler

config = Config()
msg_handler = MsgHandler()


def router_msg(msg: ChatMsg) -> str:
    """
    消息路由
    
    Args:
        msg: 聊天消息
        
    Returns:
        回复内容
    """
    # 群消息处理
    if msg.from_group():
        # 如果不是全部允许，检查是否在允许列表中（现在用群名而不是roomid）
        if not config.GROUPS.get("all_allow"):
            allow_list = config.GROUPS.get("allow_list", [])
            if msg.chat_id not in allow_list:
                return ""
        
        # 群消息需要被@才处理
        if msg.is_at_me or '@真爱粉' in msg.content or 'zaf' in msg.content:
            return msg_handler.handler_msg(msg)
        
        # 没有被@，忽略
        return ""
    
    # 私聊消息处理
    if not config.PRIVATES.get("all_allow"):
        allow_list = config.PRIVATES.get("allow_list", [])
        if msg.chat_id not in allow_list and msg.sender not in allow_list:
            return ""
    
    # 走消息处理
    return msg_handler.handler_msg(msg)
