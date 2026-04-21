# -*- coding: utf-8 -*-
"""LLM 相关配置"""
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class FallbackModel(BaseModel):
    """支持主力 + 备用的模型配置"""
    default: str = ""
    fallback: str = ""


class LLMConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    chat: FallbackModel = FallbackModel(default="openai/gpt-5.4", fallback="openai/gemini/gemini-3-pro")
    compress: FallbackModel = FallbackModel(default="openai/gpt-5.4-nano")
    vision: FallbackModel = FallbackModel(default="openai/gpt-5.4")
    image: FallbackModel = FallbackModel(default="openai/gemini/gemini-3-pro-image", fallback="openai/gpt-image-1.5", )
    image_edit: FallbackModel = FallbackModel(default="dall-e-2")
    video: FallbackModel = FallbackModel(default="gemini/veo-3.1-generate-preview", fallback="openai/sora-2-pro", )

    # Prompts
    system_prompt: str = "你是一个可爱的智能助手~"
    vision_prompt: str = "你是一个专业的图像分析助手"
    prompts: dict[str, str] = {}
    user_prompt_map: dict[str, str] = {}
