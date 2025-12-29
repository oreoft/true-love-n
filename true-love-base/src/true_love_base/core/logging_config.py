# -*- coding: utf-8 -*-
"""
Logging Config - 日志配置模块

适配 Loki 环境：
- 控制台 + 文件输出
- JSON 格式输出（Loki 友好）
- 单文件日志（不再分 info/error）
- 支持日志切分（RotatingFileHandler）
"""

import atexit
import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue
from typing import Any, Optional


class JsonFormatter(logging.Formatter):
    """
    JSON 格式化器
    
    输出结构化日志，便于 Loki/Grafana 查询和过滤
    """
    
    def __init__(self, service_name: str = "unknown"):
        super().__init__()
        self.service_name = service_name
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
        }
        
        # 添加位置信息（仅在 WARNING 及以上级别）
        if record.levelno >= logging.WARNING:
            log_data["location"] = {
                "file": record.filename,
                "function": record.funcName,
                "line": record.lineno,
            }
        
        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # 添加额外字段
        if hasattr(record, "extra_fields"):
            log_data["extra"] = record.extra_fields
        
        return json.dumps(log_data, ensure_ascii=False)


class LoggingConfig:
    """
    日志配置类（Loki 优化版）
    
    Usage:
        # 基本用法（JSON 格式，单文件）
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
    
    # 日志格式（非 JSON 模式使用）
    SIMPLE_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    @classmethod
    def setup(
        cls,
        service_name: str,
        logs_dir: str = r"\\wsl$\Ubuntu\var\log\true-love\logs",
        log_level: int = logging.INFO,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 3,
        enable_async: bool = False,
        json_format: bool = True,
    ) -> None:
        """
        设置日志配置
        
        Args:
            service_name: 服务名称，用于标识日志来源（如 server, base, ai）
            logs_dir: 日志目录，默认 "logs"
            log_level: 日志级别，默认 INFO
            max_bytes: 单个日志文件最大字节数，默认 10MB
            backup_count: 保留的备份文件数量，默认 20
            enable_async: 是否启用异步日志，默认 False
            json_format: 是否使用 JSON 格式输出，默认 True（适合 Loki）
        """
        if cls._initialized:
            return
        
        # 确保 stdout 使用 UTF-8 编码
        cls._ensure_utf8_stdout()
        
        # 确保日志目录存在
        cls._ensure_logs_dir(logs_dir)
        
        # 创建 formatter
        if json_format:
            formatter = JsonFormatter(service_name)
        else:
            formatter = logging.Formatter(cls.SIMPLE_FORMAT, cls.DATE_FORMAT)
        
        # 创建 handlers
        handlers = []
        
        # 1. 控制台 Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)
        
        # 2. 文件 Handler（单文件，包含所有级别）
        log_file = Path(logs_dir) / "app.log"
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_file),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
        
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
        logger.info(f"日志配置完成: service={service_name}, json={json_format}, async={enable_async}")
    
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
