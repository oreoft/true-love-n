# -*- coding: utf-8 -*-
"""
API Models - HTTP API 请求/响应模型

定义与外部服务通信的数据模型。
"""

import json
from dataclasses import dataclass
from typing import Any, Optional

from true_love_base.models.message import ChatMessage


@dataclass
class ChatRequest:
    """
    发送到 server 的聊天请求
    
    包装 ChatMessage，添加认证 token。
    """
    token: str
    message: ChatMessage

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        result = self.message.to_dict()  # 使用 ChatMessage.to_dict() 排除 raw_msg
        result["token"] = self.token
        return result

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


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
