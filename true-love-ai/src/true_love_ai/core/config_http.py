# -*- coding: utf-8 -*-
"""HTTP 服务与会话配置"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class HTTPConfig(BaseSettings):
    """HTTP 服务配置"""
    host: str = "0.0.0.0"
    port: int = 8088
    token: list[str] = []


class SessionConfig(BaseSettings):
    """会话配置"""
    model_config = SettingsConfigDict(extra="ignore")

    ttl_seconds: int = 86400
    compress_threshold: int = 50
    compress_keep_recent: int = 10
