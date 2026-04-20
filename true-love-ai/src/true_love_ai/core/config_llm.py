# -*- coding: utf-8 -*-
"""LLM 相关配置"""
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class ChatModels(BaseModel):
    openai:   str = "gpt-5.4"
    claude:   str = "claude-sonnet-4-5"
    gemini:   str = "gemini-3-pro"
    deepseek: str = "deepseek-chat"


class CompressModels(BaseModel):
    openai: str = "gpt-5.4-nano"


class VisionModels(BaseModel):
    openai: str = "gpt-5.4"


class ImageModels(BaseModel):
    openai: str = "gpt-image-1"
    gemini: str = "imagen-4.0-generate-001"


class VideoModels(BaseModel):
    openai: str = "sora-2-pro"
    gemini: str = "veo-3.1-generate-preview"


class LLMConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    chat:     ChatModels     = ChatModels()
    compress: CompressModels = CompressModels()
    vision:   VisionModels   = VisionModels()
    image:    ImageModels    = ImageModels()
    video:    VideoModels    = VideoModels()

    system_prompt:    str = "你是一个可爱的智能助手~"
    vision_prompt:    str = "你是一个专业的图像分析助手"
    prompts:          dict[str, str] = {}
    user_prompt_map:  dict[str, str] = {}
