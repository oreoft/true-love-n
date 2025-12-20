# -*- coding: utf-8 -*-
"""
Logging Config - 日志配置模块

提供统一的日志配置，支持：
- 控制台输出
- INFO 级别文件日志（RotatingFileHandler）
- ERROR 级别文件日志（RotatingFileHandler）
- 可选的异步日志支持
"""

import atexit
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from queue import Queue
from typing import Optional


class LoggingConfig:
    """
    日志配置类
    
    Usage:
        # 基本用法
        LoggingConfig.setup("base")
        
        # 自定义配置
        LoggingConfig.setup(
            service_name="base",
            logs_dir="logs",
            log_level=logging.INFO,
            max_bytes=10 * 1024 * 1024,  # 10MB
            backup_count=20,
            enable_async=True
        )
    """
    
    # 异步日志相关（类级别）
    _log_queue: Optional[Queue] = None
    _log_listener: Optional[logging.handlers.QueueListener] = None
    _initialized: bool = False
    
    # 日志格式
    SIMPLE_FORMAT = "%(asctime)s %(message)s"
    DETAIL_FORMAT = "%(asctime)s %(name)s %(levelname)s %(filename)s::%(funcName)s[%(lineno)d]: %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    @classmethod
    def setup(
        cls,
        service_name: str,
        logs_dir: str = "logs",
        log_level: int = logging.INFO,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 20,
        enable_async: bool = False,
        console_level: int = logging.INFO,
        file_level: int = logging.INFO,
        error_level: int = logging.ERROR,
    ) -> None:
        """
        设置日志配置
        
        Args:
            service_name: 服务名称，用于日志文件名前缀（如 server, base, ai）
            logs_dir: 日志目录，默认 "logs"
            log_level: 根日志级别，默认 INFO
            max_bytes: 单个日志文件最大字节数，默认 10MB
            backup_count: 保留的备份文件数量，默认 20
            enable_async: 是否启用异步日志，默认 False
            console_level: 控制台日志级别，默认 INFO
            file_level: INFO 文件日志级别，默认 INFO
            error_level: ERROR 文件日志级别，默认 ERROR
        """
        if cls._initialized:
            return
        
        # 确保 stdout 使用 UTF-8 编码
        cls._ensure_utf8_stdout()
        
        # 确保日志目录存在
        cls._ensure_logs_dir(logs_dir)
        
        # 创建 formatters
        simple_formatter = logging.Formatter(cls.SIMPLE_FORMAT, cls.DATE_FORMAT)
        detail_formatter = logging.Formatter(cls.DETAIL_FORMAT, cls.DATE_FORMAT)
        
        # 创建 handlers
        handlers = []
        
        # 1. 控制台 Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_handler.setFormatter(simple_formatter)
        handlers.append(console_handler)
        
        # 2. INFO 文件 Handler
        info_file = Path(logs_dir) / "info.log"
        info_handler = logging.handlers.RotatingFileHandler(
            filename=str(info_file),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        info_handler.setLevel(file_level)
        info_handler.setFormatter(simple_formatter)
        handlers.append(info_handler)
        
        # 3. ERROR 文件 Handler
        error_file = Path(logs_dir) / "error.log"
        error_handler = logging.handlers.RotatingFileHandler(
            filename=str(error_file),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        error_handler.setLevel(error_level)
        error_handler.setFormatter(detail_formatter)
        handlers.append(error_handler)
        
        # 配置根日志
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # 清除已有的 handlers
        root_logger.handlers.clear()
        
        if enable_async:
            # 异步日志模式
            cls._setup_async_logging(root_logger, handlers)
        else:
            # 同步日志模式
            for handler in handlers:
                root_logger.addHandler(handler)
        
        cls._initialized = True
        
        # 记录初始化完成
        logger = logging.getLogger("LoggingConfig")
        logger.info(f"日志配置完成: service={service_name}, async={enable_async}")
    
    @classmethod
    def _ensure_utf8_stdout(cls) -> None:
        """确保 stdout 使用 UTF-8 编码"""
        try:
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8')
            else:
                sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
        except Exception:
            pass  # 忽略编码设置失败
    
    @classmethod
    def _ensure_logs_dir(cls, logs_dir: str) -> None:
        """确保日志目录存在"""
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
    
    @classmethod
    def _setup_async_logging(
        cls,
        root_logger: logging.Logger,
        handlers: list[logging.Handler]
    ) -> None:
        """
        设置异步日志处理
        
        使用 QueueHandler 将日志放入队列，
        由 QueueListener 在后台线程写入实际的 handlers。
        """
        # 创建队列（无限大小）
        cls._log_queue = Queue(-1)
        
        # 用 QueueHandler 替换原有 handlers
        queue_handler = logging.handlers.QueueHandler(cls._log_queue)
        queue_handler.setLevel(logging.DEBUG)  # 让所有日志都进入队列
        root_logger.addHandler(queue_handler)
        
        # 创建 QueueListener，在后台线程处理日志
        cls._log_listener = logging.handlers.QueueListener(
            cls._log_queue,
            *handlers,
            respect_handler_level=True
        )
        cls._log_listener.start()
        
        # 注册退出时清理
        atexit.register(cls._cleanup_logging)
    
    @classmethod
    def _cleanup_logging(cls) -> None:
        """清理日志资源，确保所有日志都被写入"""
        if cls._log_listener:
            cls._log_listener.stop()
            cls._log_listener = None
    
    @classmethod
    def reset(cls) -> None:
        """重置日志配置（主要用于测试）"""
        cls._cleanup_logging()
        cls._initialized = False
        cls._log_queue = None
