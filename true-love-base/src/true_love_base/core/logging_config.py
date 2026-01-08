# -*- coding: utf-8 -*-
"""
Logging Config - 日志配置模块

适配 Loki 环境：
- 控制台输出（同步，实时）
- Loki 推送（异步，内置队列）
- JSON 格式输出（Loki 友好）
"""

import json
import logging
from datetime import datetime, timezone
from queue import Queue
from typing import Any

import atexit
import sys


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
    
    架构设计：
    - 控制台：同步输出，实时可见
    - Loki：异步推送，不阻塞主线程（内置队列）
    
    Usage:
        # 基本用法（仅控制台）
        LoggingConfig.setup("base")
        
        # 启用 Loki 推送
        LoggingConfig.setup(
            service_name="base",
            log_level=logging.INFO,
            enable_loki=True,
            loki_url="https://logs-prod-xxx.grafana.net",
            loki_user_id="123456",
            loki_api_key="glc_xxxxx"
        )
    """

    _initialized: bool = False
    _handlers: list[logging.Handler] = []

    # 日志格式（非 JSON 模式使用）
    SIMPLE_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    @classmethod
    def setup(
            cls,
            service_name: str,
            log_level: int = logging.INFO,
            json_format: bool = True,
            queue_size: int = 10000,
            # Loki 推送配置
            enable_loki: bool = False,
            loki_url: str = "",
            loki_user_id: str = "",
            loki_api_key: str = "",
    ) -> None:
        """
        设置日志配置
        
        架构说明：
        - 控制台 Handler：同步输出，实时可见
        - Loki Handler：异步推送（内置队列），不阻塞主线程
        
        Args:
            service_name: 服务名称，用于标识日志来源（如 server, base, ai）
            log_level: 日志级别，默认 INFO
            json_format: 是否使用 JSON 格式输出，默认 True（适合 Loki）
            queue_size: Loki 队列大小，默认 10000
            enable_loki: 是否启用 Loki 直接推送，默认 False
            loki_url: Loki API 地址（如 https://logs-prod-xxx.grafana.net）
            loki_user_id: Grafana Cloud User ID
            loki_api_key: Grafana Cloud API Key（需要 logs:write 权限）
        """
        if cls._initialized:
            logger = logging.getLogger("LoggingConfig")
            logger.warning("日志配置已初始化，忽略重复调用")
            return

        # 确保 stdout 使用 UTF-8 编码
        cls._ensure_utf8_stdout()

        # 创建 formatter
        if json_format:
            formatter = JsonFormatter(service_name)
        else:
            formatter = logging.Formatter(cls.SIMPLE_FORMAT, cls.DATE_FORMAT)

        # 配置根日志
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # 清除已有的 handlers
        root_logger.handlers.clear()
        cls._handlers.clear()

        # 1. 控制台 Handler（同步，实时输出）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        cls._handlers.append(console_handler)

        # 2. Loki Handler（异步，内置队列）
        if enable_loki and loki_url and loki_user_id and loki_api_key:
            try:
                from logging_loki import LokiQueueHandler

                loki_handler = LokiQueueHandler(
                    Queue(queue_size),
                    url=f"{loki_url.rstrip('/')}/loki/api/v1/push",
                    tags={"service_name": service_name},
                    auth=(loki_user_id, loki_api_key),
                    version="1",
                )
                loki_handler.setLevel(log_level)
                root_logger.addHandler(loki_handler)
                cls._handlers.append(loki_handler)

                print(f"[LoggingConfig] Loki Handler 已启用: {loki_url}")
            except ImportError:
                print("[LoggingConfig] 警告: 未安装 python-logging-loki，Loki 推送已禁用")
                print("[LoggingConfig] 请运行: pip install python-logging-loki")
            except Exception as e:
                print(f"[LoggingConfig] 警告: 无法创建 LokiHandler: {e}")

        cls._initialized = True

        # 注册退出时清理
        atexit.register(cls._cleanup_logging)

        # 记录初始化完成
        logger = logging.getLogger("LoggingConfig")
        logger.info(
            f"日志配置完成: service={service_name}, json={json_format}, "
            f"loki={enable_loki}"
        )

    @classmethod
    def _ensure_utf8_stdout(cls) -> None:
        """确保 stdout 使用 UTF-8 编码"""
        try:
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8')
            else:
                sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
        except Exception as e:
            # 记录编码设置失败（但不要用 logger，因为还没初始化）
            print(f"[LoggingConfig] 警告: 无法设置 stdout 编码: {e}")

    @classmethod
    def _cleanup_logging(cls) -> None:
        """清理日志资源，确保所有日志都被写入"""
        for handler in cls._handlers:
            try:
                handler.flush()
                handler.close()
            except Exception:
                pass  # 忽略清理失败

    @classmethod
    def reset(cls) -> None:
        """重置日志配置（主要用于测试）"""
        cls._cleanup_logging()
        cls._initialized = False
        cls._handlers.clear()

        # 清除根日志的所有 handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
