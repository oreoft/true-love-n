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


class Config(object):
    def __init__(self) -> None:
        self.reload()

    @staticmethod
    def _load_config() -> dict:
        pwd = os.path.dirname(os.path.abspath(__file__))
        with open(f"{pwd}/config.yaml", "rb") as fp:
            config = yaml.safe_load(fp)
        return config

    def reload(self) -> None:
        logging.config.dictConfig(self._load_config()["logging"])
