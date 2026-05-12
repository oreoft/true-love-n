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
from .config_services import PlatformKeyConfig, BaseServerConfig, NexuConfig
from true_love_common.observability.logging import LoggingConfig

LoggingConfig.setup("tl-ai")

LOG = logging.getLogger(__name__)


class Config(BaseSettings):
    """
    主配置类
    支持从 config.yaml 和环境变量加载
    """
    model_config = SettingsConfigDict(extra="ignore")

    # 每个 skill 的权限白名单，key 为 skill 名称
    # 格式：["*"] / ["wechat:*"] / ["wechat:user1", "lark:*"]
    # 未配置时所有人可用（规则1）；skill 代码/DB 中声明的权限优先（规则2）
    skill_permissions: dict[str, list[str]] = {}

    llm: Optional[LLMConfig] = None
    http: Optional[HTTPConfig] = None
    session: SessionConfig = SessionConfig()
    platform_key: PlatformKeyConfig = PlatformKeyConfig()
    base_server: BaseServerConfig = BaseServerConfig()
    nexu: NexuConfig = NexuConfig()

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
    "get_config",
    "reload_config",
]
