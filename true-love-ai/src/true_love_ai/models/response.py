#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""响应模型定义"""
from true_love_common.http.response import APIResponse, ApiResponse, BizCode
from pydantic import BaseModel, Field
from typing import Optional


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


class AudioResponse(BaseModel):
    """语音合成响应"""
    text: str = Field(..., description="合成语音使用的文本")
    audio_id: Optional[str] = Field(default=None, description="音频文件名（不含目录），路径为 gen_audio/{audio_id}.wav")
    duration_seconds: float = Field(default=0.0, description="音频时长（秒）")


__all__ = ["APIResponse", "ApiResponse", "BizCode", "ImageResponse", "VideoResponse", "AudioResponse"]
