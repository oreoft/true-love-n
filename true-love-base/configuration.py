#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging.config
import os
import sys

import yaml

# 设置日志文件夹的路径
logs_dir = "logs"

# 修改 sys.stdout 的编码为 utf-8
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

# 检查logs文件夹是否存在
if not os.path.exists(logs_dir):
    # 如果不存在，则创建该文件夹
    os.makedirs(logs_dir)


class Config(object):
    def __init__(self) -> None:
        self.config = self._load_config()
        self.set_logging()
        self.master_wix = self.config["master_wix"]
        self.http_token = self.config["http_token"]
        # 统一的监听配置（群聊和私聊不再区分）
        # 格式: [{"name": "聊天对象名称", "is_group": bool}]
        self.listen_chats: list[dict] = self.config.get("listen_chats", [])
        
        # 日志确认配置加载
        LOG = logging.getLogger("Config")
        LOG.info(f"Config loaded: master_wix={self.master_wix}")
        LOG.info(f"Config loaded: listen_chats={self.listen_chats}")

    @staticmethod
    def _load_config() -> dict:
        pwd = os.path.dirname(os.path.abspath(__file__))
        with open(f"{pwd}/config.yaml", "rb") as fp:
            config = yaml.safe_load(fp)
        return config

    def set_logging(self) -> None:
        logging.config.dictConfig(self.config["logging"])
