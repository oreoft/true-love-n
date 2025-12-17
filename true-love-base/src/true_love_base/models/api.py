# -*- coding: utf-8 -*-
"""
API Models - HTTP API 请求/响应模型

定义与外部服务通信的数据模型。
"""

import json
import os
from dataclasses import dataclass
from typing import Any, Optional

from true_love_base.models.message import BaseMessage


@dataclass
class ChatRequest:
    """
    发送到 server 的聊天请求
    
    包含消息的所有必要信息，用于 AI 处理。
    
    字段说明：
    - token: 认证 token
    - msg_type: 消息类型 ("text", "image", "voice", "video", "file", "link", "refer", "unknown")
    - sender: 发送者昵称
    - chat_id: 聊天标识（好友昵称或群名）
    - content: 消息内容
    - is_group: 是否群消息
    - is_at_me: 是否@了机器人
    - file_path: 媒体文件本地路径（图片/语音/视频/文件）
    - voice_text: 语音转文字结果
    - refer_msg: 被引用的消息（dict格式）
    """
    token: str
    msg_type: str
    sender: str
    chat_id: str
    content: str
    is_group: bool = False
    is_at_me: bool = False
    file_path: Optional[str] = None
    voice_text: Optional[str] = None
    refer_msg: Optional[dict] = None
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "token": self.token,
            "msg_type": self.msg_type,
            "sender": self.sender,
            "chat_id": self.chat_id,
            "content": self.content,
            "is_group": self.is_group,
            "is_at_me": self.is_at_me,
            "file_path": self.file_path,
            "voice_text": self.voice_text,
            "refer_msg": self.refer_msg,
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_message(cls, msg: BaseMessage, token: str) -> "ChatRequest":
        """
        从 BaseMessage 创建 ChatRequest
        
        Args:
            msg: 消息对象
            token: 认证 token
            
        Returns:
            ChatRequest 实例
        """
        from true_love_base.models.message import (
            ImageMessage,
            VoiceMessage,
            VideoMessage,
            FileMessage,
            ReferMessage,
        )
        
        # 基础字段
        request = cls(
            token=token,
            msg_type=msg.msg_type.value,
            sender=msg.sender,
            chat_id=msg.chat_id,
            content=msg.get_content(),
            is_group=msg.is_group,
            is_at_me=msg.is_at_me,
        )
        
        # 媒体消息处理
        # 注意：
        # 1. wxauto 的 download() 返回的是 pathlib.Path 对象
        # 2. 默认保存路径已在 wxauto_adapter 中通过 WxParam.DEFAULT_SAVE_PATH 设置为 server/wx_imgs
        # 3. 传给 server 时只传相对路径（wx_imgs/filename）
        if isinstance(msg, ImageMessage):
            if msg.file_path is None:
                msg.download()  # 使用 WxParam.DEFAULT_SAVE_PATH
            # 只传相对路径：wx_imgs/filename
            if msg.file_path:
                filename = os.path.basename(str(msg.file_path))
                request.file_path = f"wx_imgs/{filename}"
            
        elif isinstance(msg, VoiceMessage):
            # 语音消息：text_content 在 message_converter 转换时已经通过 to_text() 获取
            # 这里直接使用，不再调用 download()（VoiceMessage 没有该方法）
            request.voice_text = msg.text_content
            # 如果有转文字结果，用它作为 content
            if msg.text_content:
                request.content = msg.text_content
                
        elif isinstance(msg, VideoMessage):
            if msg.file_path is None:
                msg.download()  # 使用 WxParam.DEFAULT_SAVE_PATH
            if msg.file_path:
                filename = os.path.basename(str(msg.file_path))
                request.file_path = f"wx_imgs/{filename}"
            
        elif isinstance(msg, FileMessage):
            if msg.file_path is None:
                msg.download()  # 使用 WxParam.DEFAULT_SAVE_PATH
            if msg.file_path:
                filename = os.path.basename(str(msg.file_path))
                request.file_path = f"wx_imgs/{filename}"
            
        elif isinstance(msg, ReferMessage):
            if msg.referred_msg:
                request.refer_msg = msg.referred_msg.to_dict()
        
        return request


@dataclass
class ChatResponse:
    """
    Server 返回的响应
    """
    code: int  # 状态码，0 表示成功
    message: str  # 状态消息
    data: Optional[str] = None  # 返回的回复内容
    
    @classmethod
    def from_dict(cls, d: dict) -> "ChatResponse":
        """从字典创建"""
        return cls(
            code=d.get("code", -1),
            message=d.get("message", ""),
            data=d.get("data"),
        )
    
    @property
    def is_success(self) -> bool:
        """是否成功"""
        return self.code == 0


@dataclass
class ApiResponse:
    """
    通用 API 响应模型
    """
    code: int
    message: str
    data: Any = None
    
    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "data": self.data,
        }
    
    @classmethod
    def success(cls, data: Any = None, message: str = "success") -> "ApiResponse":
        """成功响应"""
        return cls(code=0, message=message, data=data)
    
    @classmethod
    def error(cls, code: int, message: str) -> "ApiResponse":
        """错误响应"""
        return cls(code=code, message=message, data=None)


# 预定义的错误响应
class ApiErrors:
    """API 错误定义"""
    ROBOT_NOT_READY = ApiResponse.error(101, "Robot not ready")
    SEND_FAILED = ApiResponse.error(102, "Send failed, please retry")
    INVALID_PARAMS = ApiResponse.error(103, "Invalid parameters")
    INTERNAL_ERROR = ApiResponse.error(500, "Internal server error")
