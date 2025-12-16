#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration - 配置管理模块

提供配置加载和日志设置功能。
使用单例模式确保配置只加载一次。
支持异步日志以提升性能。
"""

import atexit
import logging
import logging.config
import logging.handlers
import os
import sys
from queue import Queue
from typing import Optional

import yaml

# 设置日志文件夹的路径
logs_dir = "logs"

# 修改 sys.stdout 的编码为 utf-8
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

# 检查logs文件夹是否存在
if not os.path.exists(logs_dir):
    # 如果不存在，则创建该文件夹
    os.makedirs(logs_dir)


class Config:
    """
    配置管理类（单例模式）
    
    确保配置只加载一次，支持异步日志。
    """
    _instance: Optional["Config"] = None
    _initialized: bool = False
    
    # 异步日志相关
    _log_queue: Optional[Queue] = None
    _log_listener: Optional[logging.handlers.QueueListener] = None
    
    def __new__(cls) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        # 防止重复初始化
        if Config._initialized:
            return
        
        self.config = self._load_config()
        self._setup_logging()
        
        self.master_wix = self.config["master_wix"]
        self.http_token = self.config["http_token"]
        
        # 监听列表文件路径（与 config.yaml 同级目录）
        self.listen_chats_file = self._get_listen_chats_file()
        
        Config._initialized = True
        
        # 日志确认配置加载
        LOG = logging.getLogger("Config")
        LOG.info(f"Config loaded: master_wix={self.master_wix}")
        LOG.info(f"Config loaded: listen_chats_file={self.listen_chats_file}")
        LOG.info("Async logging enabled")

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

    def _setup_logging(self) -> None:
        """设置日志（包含异步日志）"""
        # 先用 dictConfig 配置基础日志
        logging.config.dictConfig(self.config["logging"])
        
        # 设置异步日志
        self._setup_async_logging()
    
    def _setup_async_logging(self) -> None:
        """
        设置异步日志处理
        
        使用 QueueHandler 将日志放入队列，
        由 QueueListener 在后台线程写入实际的 handlers。
        """
        root_logger = logging.getLogger()
        
        # 保存原有的 handlers
        original_handlers = root_logger.handlers[:]
        
        if not original_handlers:
            return
        
        # 创建队列（无限大小）
        Config._log_queue = Queue(-1)
        
        # 用 QueueHandler 替换原有 handlers
        queue_handler = logging.handlers.QueueHandler(Config._log_queue)
        queue_handler.setLevel(logging.DEBUG)  # 让所有日志都进入队列
        root_logger.handlers = [queue_handler]
        
        # 创建 QueueListener，在后台线程处理日志
        Config._log_listener = logging.handlers.QueueListener(
            Config._log_queue,
            *original_handlers,
            respect_handler_level=True
        )
        Config._log_listener.start()
        
        # 注册退出时清理
        atexit.register(Config._cleanup_logging)
    
    @classmethod
    def _cleanup_logging(cls) -> None:
        """清理日志资源，确保所有日志都被写入"""
        if cls._log_listener:
            cls._log_listener.stop()
            cls._log_listener = None
