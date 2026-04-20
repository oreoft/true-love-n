# -*- coding: utf-8 -*-
"""
配置管理模块
主配置类，从各子模块聚合所有配置段。
"""
import logging
from typing import Optional

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

from .config_llm import LLMConfig
from .config_http import HTTPConfig, SessionConfig
from .config_services import PlatformKeyConfig, BaseServerConfig, NexuConfig, MuninnConfig, GithubConfig
from .logging_config import LoggingConfig

LoggingConfig.setup("tl-ai")

LOG = logging.getLogger(__name__)


class Config(BaseSettings):
    """
    主配置类
    支持从 config.yaml 和环境变量加载
    """
    model_config = SettingsConfigDict(extra="ignore")

    default_provider: str = "openai"

    # 每个 skill 的允许用户列表，key 为 skill 名称，"default" 为兜底
    # 未配置某 skill 时走 default；default 也未配置时所有人可用
    skill_permissions: dict[str, list[str]] = {}

    llm: Optional[LLMConfig] = None
    http: Optional[HTTPConfig] = None
    session: SessionConfig = SessionConfig()
    platform_key: PlatformKeyConfig = PlatformKeyConfig()
    base_server: BaseServerConfig = BaseServerConfig()
    nexu: NexuConfig = NexuConfig()
    muninn: MuninnConfig = MuninnConfig()
    github: GithubConfig = GithubConfig()

    logging: Optional[dict] = None

    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> "Config":
        LOG.info(f"从 {path} 加载配置...")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)


_config: Optional[Config] = None


def get_config() -> Config:
    global _config
    if _config is None:
        import os
        app_env = os.environ.get("APP_ENV", "")
        path = "config.yaml" if app_env == "prod" else "config-dev.yaml"
        _config = Config.from_yaml(path)
    return _config


def reload_config() -> Config:
    global _config
    _config = Config.from_yaml()
    return _config


__all__ = [
    "Config",
    "LLMConfig",
    "HTTPConfig",
    "SessionConfig",
    "PlatformKeyConfig",
    "BaseServerConfig",
    "NexuConfig",
    "MuninnConfig",
    "GithubConfig",
    "get_config",
    "reload_config",
]
