#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
使用 Pydantic Settings 进行类型安全的配置管理
"""
import logging
from typing import Optional

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

from .logging_config import LoggingConfig

# 初始化日志配置（在加载任何配置之前）
LoggingConfig.setup("tl-ai")

LOG = logging.getLogger(__name__)


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
    default_model: str = "openai/gpt-5.2"  # 默认聊天模型
    # 图像多态配置
    vision_model: str = "gpt-5.2"  # 图像分析模型

    # 聊天模型
    deepseek_model: str = "deepseek/deepseek-chat"  # DeepSeek 模型
    claude_model: str = "claude-sonnet-4-5"  # Claude 模型
    gemini_model: str = "gemini-3-pro-preview"  # Gemini 模型

    # 图像生成配置
    image_model: str = "dall-e-3"  # 图像生成模型
    gemini_image_model: str = "gemini-3-pro-image-preview"  # Gemini 图像模型

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
    litellm_api_key: str = ""
    litellm_base_url: str = ""


class BaseServerConfig(BaseSettings):
    """内部 Base / Server 服务配置"""
    model_config = SettingsConfigDict(extra="ignore")

    host: str = ""
    self_wxid: str = ""   # 机器人微信 ID
    master_wxid: str = ""  # 主人微信 ID
    master_group: str = ""  # 主人群组


class NexuConfig(BaseSettings):
    """Nexu 服务配置"""
    model_config = SettingsConfigDict(extra="ignore")

    base_url: str = "http://nexu:3010"
    token: str = ""


class MuninnConfig(BaseSettings):
    """Muninn CDK 服务配置"""
    model_config = SettingsConfigDict(extra="ignore")

    api_base_url: str = ""
    admin_token: str = ""
    allow_user: list[str] = []


class GithubConfig(BaseSettings):
    """GitHub Actions 部署配置"""
    model_config = SettingsConfigDict(extra="ignore")

    token: str = ""
    allow_user: list[str] = []


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
    nexu: NexuConfig = NexuConfig()
    muninn: MuninnConfig = MuninnConfig()
    github: GithubConfig = GithubConfig()

    # 日志配置
    logging: Optional[dict] = None

    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> "Config":
        """从 YAML 文件加载配置"""
        LOG.info(f"从 {path} 加载配置...")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # 注意：日志配置已改用 LoggingConfig 类，不再从 YAML 加载

        return cls(**data)


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取配置单例"""
    global _config
    if _config is None:
        import os
        app_env = os.environ.get("APP_ENV", "")
        path = "config.yaml" if app_env == "prod" else "config-dev.yaml"
        _config = Config.from_yaml(path)
    return _config


def reload_config() -> Config:
    """重新加载配置"""
    global _config
    _config = Config.from_yaml()
    return _config
