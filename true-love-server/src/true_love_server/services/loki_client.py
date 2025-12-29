# -*- coding: utf-8 -*-
"""
Loki Client - Loki 日志查询客户端

通过 Grafana Cloud API 代理查询 Loki 日志。
"""

import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List

import requests

from ..core import Config

LOG = logging.getLogger("LokiClient")


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: int  # 毫秒时间戳
    time_str: str  # 格式化时间字符串
    level: str  # 日志等级
    service: str  # 服务名称
    content: str  # 日志内容
    raw: str  # 原始日志行

    def to_dict(self) -> dict:
        return asdict(self)


class LokiClient:
    """Loki 客户端 - 通过 Grafana API 代理访问"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        config = Config()
        loki_config = getattr(config, 'LOKI', {}) or {}

        self.grafana_url = loki_config.get('grafana_url', '').rstrip('/')
        self.api_token = loki_config.get('api_token', '')
        self.datasource_uid = loki_config.get('datasource_uid', 'grafanacloud-logs')
        self.services = loki_config.get('services', ['tl-ai', 'tl-base', 'tl-server'])

        self._initialized = True
        LOG.info(f"LokiClient 初始化完成, grafana_url: {self.grafana_url}, datasource: {self.datasource_uid}")

    def _get_headers(self) -> dict:
        """获取请求头"""
        return {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }

    def _build_query(self) -> str:
        """构建 LogQL 查询语句"""
        services_regex = '|'.join(self.services)
        return f'{{service_name=~"{services_regex}"}}'

    def _parse_log_line(self, line: str, labels: dict, ts_ns: int) -> LogEntry:
        """
        解析日志行
        
        Loki 返回的数据结构：
        - labels 中包含 service_name, level 等信息
        - line 是纯日志内容
        """
        # 从 labels 获取服务名和等级
        service = labels.get('service_name', labels.get('service', 'unknown'))
        level = labels.get('level', 'INFO').upper()

        # 标准化 level
        if level == 'WARNING':
            level = 'WARN'
        if level not in ('INFO', 'WARN', 'ERROR', 'DEBUG'):
            level = 'INFO'

        # 从时间戳生成时间字符串
        dt = datetime.fromtimestamp(ts_ns / 1_000_000_000)
        time_str = dt.strftime('%Y-%m-%d %H:%M:%S.') + f'{dt.microsecond // 1000:03d}'

        return LogEntry(
            timestamp=ts_ns // 1_000_000,  # 转为毫秒
            time_str=time_str,
            level=level,
            service=service,
            content=line.strip(),
            raw=line
        )

    def query_range(
            self,
            start_ns: int,
            end_ns: int,
            limit: int = 50,
            direction: str = 'backward'
    ) -> dict:
        """
        查询时间范围内的日志
        
        Args:
            start_ns: 开始时间（纳秒时间戳）
            end_ns: 结束时间（纳秒时间戳）
            limit: 最大返回条数
            direction: 排序方向 forward/backward
        
        Returns:
            {
                "success": bool,
                "logs": [LogEntry...],
                "earliest_ns": int,  # 返回数据中最早的时间戳（纳秒）
                "latest_ns": int,    # 返回数据中最新的时间戳（纳秒）
                "message": str
            }
        """
        if not self.grafana_url or not self.api_token:
            return {
                "success": False,
                "logs": [],
                "earliest_ns": 0,
                "latest_ns": 0,
                "message": "Loki 配置不完整，请检查 config.yaml 中的 loki 配置"
            }

        query = self._build_query()

        # Grafana 数据源代理 API
        url = f"{self.grafana_url}/api/datasources/proxy/uid/{self.datasource_uid}/loki/api/v1/query_range"

        params = {
            'query': query,
            'start': start_ns,
            'end': end_ns,
            'limit': limit,
            'direction': direction
        }

        try:
            start_time = time.time()

            resp = requests.get(url, headers=self._get_headers(), params=params, timeout=(5, 30))
            resp.raise_for_status()

            data = resp.json()
            cost_ms = (time.time() - start_time) * 1000

            if data.get('status') != 'success':
                LOG.error(f"Loki 查询失败: {data}")
                return {
                    "success": False,
                    "logs": [],
                    "earliest_ns": 0,
                    "latest_ns": 0,
                    "message": f"Loki 返回错误: {data.get('error', 'unknown')}"
                }

            # 解析结果
            logs: List[LogEntry] = []
            earliest_ns = end_ns
            latest_ns = start_ns

            result = data.get('data', {}).get('result', [])
            for stream in result:
                labels = stream.get('stream', {})
                values = stream.get('values', [])

                for ts_ns_str, line in values:
                    ts_ns = int(ts_ns_str)
                    entry = self._parse_log_line(line, labels, ts_ns)
                    logs.append(entry)

                    earliest_ns = min(earliest_ns, ts_ns)
                    latest_ns = max(latest_ns, ts_ns)

            # 按时间戳排序（从旧到新，方便前端展示）
            logs.sort(key=lambda x: x.timestamp)

            return {
                "success": True,
                "logs": logs,
                "earliest_ns": earliest_ns if logs else start_ns,
                "latest_ns": latest_ns if logs else end_ns,
                "message": ""
            }

        except requests.exceptions.Timeout:
            LOG.error("Loki 查询超时")
            return {
                "success": False,
                "logs": [],
                "earliest_ns": 0,
                "latest_ns": 0,
                "message": "查询超时，请稍后重试"
            }
        except requests.exceptions.HTTPError as e:
            LOG.error(f"Loki HTTP 错误: {e}")
            error_msg = str(e)
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('message', str(e))
                except:
                    pass
            return {
                "success": False,
                "logs": [],
                "earliest_ns": 0,
                "latest_ns": 0,
                "message": f"HTTP 错误: {error_msg}"
            }
        except Exception as e:
            LOG.exception(f"Loki 查询异常: {e}")
            return {
                "success": False,
                "logs": [],
                "earliest_ns": 0,
                "latest_ns": 0,
                "message": str(e)
            }


# 单例获取函数
_loki_client: Optional[LokiClient] = None


def get_loki_client() -> LokiClient:
    """获取 LokiClient 单例"""
    global _loki_client
    if _loki_client is None:
        _loki_client = LokiClient()
    return _loki_client
