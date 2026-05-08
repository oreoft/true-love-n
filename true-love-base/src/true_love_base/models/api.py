# -*- coding: utf-8 -*-
"""
API Models - HTTP API 请求/响应模型

定义与外部服务通信的数据模型。
"""

import json
from dataclasses import dataclass
from typing import Any, Optional

from true_love_common.chat_msg import ChatMsg
from true_love_common.http.response import ApiResponse, BizCode


@dataclass
class ChatRequest:
    """发送到 server 的聊天请求，包装 ChatMsg 并附加认证 token。"""
    token: str
    message: ChatMsg

    def to_dict(self) -> dict[str, Any]:
        return {"token": self.token, "msg": self.message.to_dict()}

    def to_json(self) -> str:
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


# 预定义的错误响应
class ApiErrors:
    """API 错误定义"""
    ROBOT_NOT_READY = ApiResponse.error(BizCode.ROBOT_NOT_READY, "Robot not ready")
    SEND_FAILED = ApiResponse.error(BizCode.SEND_FAILED, "Send failed, please retry")
    INVALID_PARAMS = ApiResponse.error(BizCode.TOKEN_ERROR, "Invalid parameters")
    INTERNAL_ERROR = ApiResponse.error(BizCode.INTERNAL_ERROR, "Internal server error")
