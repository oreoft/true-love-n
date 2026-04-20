# -*- coding: utf-8 -*-
"""LLM 相关配置"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """LLM 配置"""
    model_config = SettingsConfigDict(extra="ignore")


    # OpenAI Keys（多 Key 负载均衡）
    key1: str = ""
    key2: str = ""
    key3: str = ""

    # Claude
    claude_key1: str = ""

    # DeepSeek
    ds_key1: str = ""

    # Gemini
    gemini_key1: str = ""

    # 模型配置
    default_model: str = "openai/gpt-5.4"
    compress_model: str = "openai/gpt-5.4-nano"
    vision_model: str = "gpt-5.4"

    # 各提供商聊天模型
    claude_model: str = "claude-sonnet-4-5"
    gemini_model: str = "gemini-3-pro"

    # 图像生成
    image_model: str = "dall-e-3"
    gemini_image_model: str = "gemini-3-pro-image"

    # 视频生成
    openai_video_model: str = "sora-2-pro"
    gemini_video_model: str = "veo-3.1-generate-preview"

    # 使用 prompt2 的用户列表
    prompt2_users: list[str] = []

    # System Prompts
    prompt: str = "你是一个可爱的智能助手~"
    prompt2: str = "你是一个可爱的智能助手~"
    prompt3: str = "你是一个可爱的智能助手~"
    prompt4: str = "你是一个专业的图像描述词生成器，请生成适合 AI 绘图的英文 prompt"
    prompt5: str = "根据用户描述判断图像操作类型"
    prompt6: str = "你是一个专业的图像分析助手"
