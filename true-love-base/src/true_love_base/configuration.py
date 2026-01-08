#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration - 配置管理模块

提供配置加载功能。
使用单例模式确保配置只加载一次。
日志配置使用 LoggingConfig 类。
"""

import logging
from typing import Optional

import yaml

from .core.logging_config import LoggingConfig
from .utils.path_resolver import get_listen_chats_file


class Config:
    """
    配置管理类（单例模式）
    
    确保配置只加载一次。
    """
    _instance: Optional["Config"] = None
    _initialized: bool = False
    
    def __new__(cls) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        # 防止重复初始化
        if Config._initialized:
            return
        
        self.config = self._load_config()
        
        # 先初始化日志系统（使用配置文件中的 loki 配置）
        self._setup_logging()
        
        self.master_wix = self.config["master_wix"]
        self.http_token = self.config["http_token"]
        
        # 监听列表文件路径（与 config.yaml 同级目录）
        self.listen_chats_file = get_listen_chats_file()
        
        Config._initialized = True
        
        # 日志确认配置加载
        LOG = logging.getLogger("Config")
        LOG.info(f"Config loaded: master_wix={self.master_wix}")
        LOG.info(f"Config loaded: listen_chats_file={self.listen_chats_file}")
    
    def _setup_logging(self) -> None:
        """设置日志系统（从配置文件读取 Loki 配置）"""
        loki_config = self.config.get("loki", {}) or {}
        
        LoggingConfig.setup(
            service_name="tl-base",
            logs_dir="logs",
            log_level=logging.INFO,
            enable_async=True,
            json_format=True,
            enable_loki=loki_config.get("enable", False),
            loki_url=loki_config.get("loki_url", ""),
            loki_user_id=loki_config.get("user_id", ""),
            loki_api_key=loki_config.get("api_key", ""),
        )

    @staticmethod
    def _load_config() -> dict:
        """从当前工作目录读取配置文件"""
        config_path = "config.yaml"
        with open(config_path, "r", encoding='utf-8') as fp:
            config = yaml.safe_load(fp)
        return config

    @staticmethod
    def _get_listen_chats_file() -> str:
        """获取监听列表文件路径（与 config.yaml 同级目录）"""
        return "listen_chats.json"
