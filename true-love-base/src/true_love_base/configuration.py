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
        
        # 监听列表文件路径（与 config.yaml 同级目录）
        self.listen_chats_file = self._get_listen_chats_file()
        
        # 日志确认配置加载
        LOG = logging.getLogger("Config")
        LOG.info(f"Config loaded: master_wix={self.master_wix}")
        LOG.info(f"Config loaded: listen_chats_file={self.listen_chats_file}")

    @staticmethod
    def _load_config() -> dict:
        # 从当前工作目录读取配置文件（需从 pyproject.toml 同级目录运行）
        config_path = "config.yaml"
        with open(config_path, "r", encoding='utf-8') as fp:
            config = yaml.safe_load(fp)
        return config

    @staticmethod
    def _get_listen_chats_file() -> str:
        """获取监听列表文件路径（与 config.yaml 同级目录）"""
        return "listen_chats.json"

    def set_logging(self) -> None:
        logging.config.dictConfig(self.config["logging"])
