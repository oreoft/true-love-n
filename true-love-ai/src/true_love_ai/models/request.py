#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
请求模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    """聊天请求"""
    token: str = Field(..., description="鉴权 Token")
    content: str = Field(..., description="消息内容")
    wxid: str = Field(default="", description="会话 ID")
    sender: str = Field(default="", description="发送者")
    
    # 可选：指定模型提供商和模型
    provider: Optional[str] = Field(default=None, description="模型提供商: openai/claude/deepseek/gemini")
    model: Optional[str] = Field(default=None, description="指定模型名称")


class ImageRequest(BaseModel):
    """图像生成请求"""
    token: str = Field(..., description="鉴权 Token")
    content: str = Field(..., description="图像描述或操作指令")
    img_data: Optional[str] = Field(default=None, description="base64 编码的图像（图生图时使用）")
    wxid: str = Field(default="", description="会话 ID")
    sender: str = Field(default="", description="发送者")
    
    # 可选：指定模型提供商和模型
    provider: Optional[str] = Field(default=None, description="图像提供商: openai/stability/gemini")
    model: Optional[str] = Field(default=None, description="指定模型名称")


class ImageTypeRequest(BaseModel):
    """图像类型判断请求"""
    token: str = Field(..., description="鉴权 Token")
    content: str = Field(..., description="用户描述")
    
    # 可选：指定模型
    provider: Optional[str] = Field(default=None, description="模型提供商")
    model: Optional[str] = Field(default=None, description="指定模型名称")


class AnalyzeRequest(BaseModel):
    """图像分析请求"""
    token: str = Field(..., description="鉴权 Token")
    content: str = Field(..., description="分析问题")
    img_data: str = Field(..., description="base64 编码的图像")
    wxid: str = Field(default="", description="会话 ID")
    sender: str = Field(default="", description="发送者")
    
    # 可选：指定模型
    provider: Optional[str] = Field(default=None, description="模型提供商: openai/claude/gemini")
    model: Optional[str] = Field(default=None, description="指定模型名称")


class VideoRequest(BaseModel):
    """视频生成请求"""
    token: str = Field(..., description="鉴权 Token")
    content: str = Field(..., description="视频描述")
    img_data_list: Optional[list[str]] = Field(default=None, description="base64 编码的图像列表（图生视频时使用）")
    wxid: str = Field(default="", description="会话 ID")
    sender: str = Field(default="", description="发送者")
    
    # 可选：指定模型提供商和模型
    provider: Optional[str] = Field(default=None, description="视频提供商: openai/gemini")
    model: Optional[str] = Field(default=None, description="指定模型名称")
