#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging.config
import os

import yaml

# 设置日志文件夹的路径
logs_dir = "logs"

# 检查logs文件夹是否存在
if not os.path.exists(logs_dir):
    # 如果不存在，则创建该文件夹
    os.makedirs(logs_dir)


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
        pwd = os.path.dirname(os.path.abspath(__file__))
        config_path = f"{pwd}/config.yaml"
        # 如果这里有问题, 直接不让服务启动
        with open(config_path, "r") as fp:
            return yaml.safe_load(fp)

    def reload(self) -> None:
        yconfig = self._load_config()
        if yconfig:
            logging.config.dictConfig(yconfig.get("logging", {}))
            self.GROUPS: dict = yconfig["groups"]
            self.PRIVATES: dict = yconfig["privates"]
            self.ENABLE_BOT: dict = yconfig["enable_bot"]
            self.LLM_BOT: dict = yconfig.get(self.ENABLE_BOT, None)
            self.GITHUB:dict = yconfig.get("github", {})
            self.HTTP = yconfig.get("http")
            self.BASE_SERVER: dict = yconfig.get("base_server")
            self.CARD: dict = yconfig.get("card", {})
