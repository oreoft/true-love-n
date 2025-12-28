#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

import yaml

from .logging_config import LoggingConfig

# 初始化日志配置（在加载任何配置之前）
LoggingConfig.setup("server")

LOG = logging.getLogger("Configuration")


class Config:
    _instance = None

    def __new__(cls):
        """new是魔法方法 实例化的时候会调用一次 用它来实现单例"""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance.reload()
        return cls._instance

    @staticmethod
    def _load_config() -> dict:
        # 从当前工作目录读取配置文件（而非包内部）
        config_path = "config.yaml"
        LOG.info("_load_config 开始刷新配置")
        # 如果这里有问题, 直接不让服务启动
        with open(config_path, "r", encoding='utf-8') as fp:
            updated_config = yaml.safe_load(fp)
        LOG.info("_load_config 刷新配置成功: [%s]", updated_config)
        return updated_config

    def reload(self) -> None:
        yconfig = self._load_config()
        if yconfig:
            # 注意：日志配置已改用 LoggingConfig 类，不再从 YAML 加载
            # 注意：groups/privates 的 allow_list 已移至 base 端
            # 这里保留是为了兼容 auto_notice 等功能
            # 也支持新的顶层 auto_notice 配置
            self.AUTO_NOTICE: dict = yconfig.get("auto_notice", self.GROUPS.get("auto_notice", {}))
            self.ENABLE_BOT: dict = yconfig["enable_bot"]
            self.LLM_BOT: dict = yconfig.get(self.ENABLE_BOT, None)
            self.HTTP_TOKEN: dict = yconfig.get("http_token")
            self.BASE_SERVER: dict = yconfig.get("base_server")
            self.REMAINDER: dict = yconfig.get("remainder", {})
            self.ASR: dict = yconfig.get("asr", {})
            self.BROWSERLESS: str = yconfig.get("browserless", "")
            self.AI_SERVICE: dict = yconfig.get("ai_service", {})
            self.ALAPI: dict = yconfig.get("alapi", {})
