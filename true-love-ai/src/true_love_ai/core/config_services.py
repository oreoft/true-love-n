# -*- coding: utf-8 -*-
"""外部服务配置"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class PlatformKeyConfig(BaseSettings):
    """第三方平台 Key"""
    sd: str = ""
    litellm_api_key: str = ""
    litellm_base_url: str = ""


class BaseServerConfig(BaseSettings):
    """内部 Base / Server 服务配置"""
    model_config = SettingsConfigDict(extra="ignore")

    host: str = ""
    self_wxid: str = ""
    master_wxid: str = ""
    master_group: str = ""


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
