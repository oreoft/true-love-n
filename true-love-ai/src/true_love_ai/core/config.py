#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
使用 Pydantic Settings 进行类型安全的配置管理
"""
import logging
import logging.config
import os
from typing import Optional

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

LOG = logging.getLogger(__name__)

# 确保 logs 目录存在
if not os.path.exists("logs"):
    os.makedirs("logs")


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
    default_model: str = "gpt-5.2"  # 默认聊天模型
    # 图像多态配置
    vision_model: str = "gpt-5.2"  # 图像分析模型

    # 聊天模型
    deepseek_model: str = "deepseek/deepseek-chat"  # DeepSeek 模型
    claude_model: str = "claude-sonnet-4-5"  # Claude 模型
    gemini_model: str = "gemini-3-pro"  # Gemini 模型

    # 图像生成配置
    image_model: str = "dall-e-3"  # 图像生成模型
    gemini_image_model: str = "gemini-3-pro-image"  # Gemini 图像模型

    # 视频生成配置
    openai_video_model: str = "sora-2-pro"  # OpenAI 视频模型
    gemini_video_model: str = "veo-3.1-generate-preview"  # Gemini 视频模型

    # 使用 prompt2 的用户列表（特殊用户使用不同的系统提示词）
    prompt2_users: list[str] = []

    # System Prompts
    prompt: str = "你是一个可爱的智能助手~"
    prompt2: str = "你是一个可爱的智能助手~"  # prompt2_users 用户专用
    prompt3: str = "你是一个可爱的智能助手~"  # 询问功能
    prompt4: str = "你是一个专业的图像描述词生成器，请生成适合 AI 绘图的英文 prompt"
    prompt5: str = "根据用户描述判断图像操作类型"
    prompt6: str = "你是一个专业的图像分析助手"


class HTTPConfig(BaseSettings):
    """HTTP 服务配置"""
    host: str = "0.0.0.0"
    port: int = 8088
    token: list[str] = []


class SessionConfig(BaseSettings):
    """会话配置"""
    max_history: int = 50  # 默认最大对话历史长度
    ttl_seconds: int = 86400  # 24小时


class PlatformKeyConfig(BaseSettings):
    """第三方平台 Key"""
    sd: str = ""  # Stability AI


class BaseServerConfig(BaseSettings):
    """Base 服务配置"""
    model_config = SettingsConfigDict(extra="ignore")

    host: str = "http://localhost:5000/send-text"
    self_wxid: str = ""  # 机器人微信ID
    master_wxid: str = ""  # 主人微信ID
    master_group: str = ""  # 主人群组


class Config(BaseSettings):
    """
    主配置类
    支持从 config.yaml 和环境变量加载
    """
    model_config = SettingsConfigDict(
        extra="ignore"
    )

    # 默认服务提供商 (openai/claude/deepseek/gemini)
    default_provider: str = "openai"

    # 各模块配置
    chatgpt: Optional[LLMConfig] = None
    http: Optional[HTTPConfig] = None
    session: SessionConfig = SessionConfig()
    platform_key: PlatformKeyConfig = PlatformKeyConfig()
    base_server: BaseServerConfig = BaseServerConfig()

    # 日志配置
    logging: Optional[dict] = None

    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> "Config":
        """从 YAML 文件加载配置"""
        LOG.info(f"从 {path} 加载配置...")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # 配置日志
        if "logging" in data:
            logging.config.dictConfig(data["logging"])

        return cls(**data)


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取配置单例"""
    global _config
    if _config is None:
        _config = Config.from_yaml()
    return _config


def reload_config() -> Config:
    """重新加载配置"""
    global _config
    _config = Config.from_yaml()
    return _config
