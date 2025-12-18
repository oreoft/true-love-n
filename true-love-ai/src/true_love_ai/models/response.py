#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
响应模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional, Any


class APIResponse(BaseModel):
    """统一 API 响应格式"""
    code: int = Field(default=0, description="状态码，0 表示成功")
    message: str = Field(default="success", description="消息")
    data: Optional[Any] = Field(default=None, description="响应数据")
    
    @classmethod
    def success(cls, data: Any = None) -> "APIResponse":
        """成功响应"""
        return cls(code=0, message="success", data=data)
    
    @classmethod
    def error(cls, code: int, message: str) -> "APIResponse":
        """错误响应"""
        return cls(code=code, message=message, data=None)
    
    @classmethod
    def token_error(cls) -> "APIResponse":
        """Token 错误"""
        return cls(code=103, message="failed token check", data=None)
    
    @classmethod
    def internal_error(cls, message: str = "发生未知错误, 稍后再试试捏") -> "APIResponse":
        """内部错误"""
        return cls(code=105, message=message, data=None)


class ChatResponse(BaseModel):
    """聊天响应数据"""
    type: str = Field(..., description="响应类型: chat/search/gen-img")
    answer: str = Field(..., description="回答内容")
    debug: Optional[str] = Field(default=None, description="调试信息")


class ImageResponse(BaseModel):
    """图像响应数据"""
    prompt: str = Field(..., description="使用的 prompt")
    img: str = Field(..., description="base64 编码的图像")


class ImageTypeResponse(BaseModel):
    """图像类型响应数据"""
    type: str = Field(..., description="操作类型: gen_by_img/erase_img/replace_img/analyze_img/remove_background_img")
    answer: str = Field(..., description="操作描述词")
