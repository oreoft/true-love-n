#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""响应模型定义"""
from pydantic import BaseModel, Field
from typing import Optional, Any


class APIResponse(BaseModel):
    """统一 API 响应格式"""
    code: int = Field(default=0)
    message: str = Field(default="success")
    data: Optional[Any] = Field(default=None)

    @classmethod
    def success(cls, data: Any = None) -> "APIResponse":
        return cls(code=0, message="success", data=data)

    @classmethod
    def error(cls, message: str) -> "APIResponse":
        return cls(code=1, message=message, data=None)

    @classmethod
    def token_error(cls) -> "APIResponse":
        return cls(code=103, message="failed token check", data=None)

    @classmethod
    def internal_error(cls, message: str = "发生未知错误, 稍后再试试捏") -> "APIResponse":
        return cls(code=105, message=message, data=None)


class ImageResponse(BaseModel):
    """图像生成响应"""
    prompt: str = Field(..., description="使用的 prompt")
    img: str = Field(..., description="base64 编码的图像")


class VideoResponse(BaseModel):
    """视频生成响应"""
    prompt: str = Field(..., description="使用的 prompt")
    video_url: Optional[str] = Field(default=None)
    video_base64: Optional[str] = Field(default=None)
    video_id: Optional[str] = Field(default=None, description="视频文件名（不含目录），路径为 gen_video/{video_id}.mp4")
