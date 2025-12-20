# -*- coding: utf-8 -*-
"""
Log Service - 日志查询服务

提供日志文件的增量查询功能。
"""

import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

LOG = logging.getLogger("LogService")


class LogType(str, Enum):
    """日志类型"""
    INFO = "info"
    ERROR = "error"


@dataclass
class LogQueryResult:
    """日志查询结果"""
    lines: list[str]  # 日志行列表
    next_offset: int  # 下次查询的偏移量
    total_lines: int  # 本次返回的行数
    has_more: bool  # 是否还有更多内容


class LogQueryService:
    """
    日志查询服务类
    
    支持增量查询日志文件，通过文件字节偏移实现。
    """
    
    # 最大查询行数限制
    MAX_LIMIT = 500
    # 默认查询行数
    DEFAULT_LIMIT = 100
    
    def __init__(self, logs_dir: Optional[str] = None):
        """
        初始化日志查询服务
        
        Args:
            logs_dir: 日志目录路径，默认为项目根目录下的 logs 目录
        """
        if logs_dir:
            self._logs_dir = Path(logs_dir)
        else:
            # 默认使用当前工作目录下的 logs 目录
            self._logs_dir = Path.cwd() / "logs"
    
    def _get_log_file_path(self, log_type: LogType) -> Path:
        """
        获取日志文件路径
        
        Args:
            log_type: 日志类型
            
        Returns:
            日志文件路径
        """
        filename = f"{log_type.value}.log"
        return self._logs_dir / filename
    
    def _validate_limit(self, limit: Optional[int]) -> int:
        """
        校验并返回有效的 limit 值
        
        Args:
            limit: 请求的行数限制
            
        Returns:
            校验后的 limit 值
        """
        if limit is None or limit <= 0:
            return self.DEFAULT_LIMIT
        return min(limit, self.MAX_LIMIT)
    
    def query_logs(
        self,
        log_type: LogType,
        since_offset: Optional[int] = None,
        limit: Optional[int] = None
    ) -> LogQueryResult:
        """
        查询日志
        
        Args:
            log_type: 日志类型 (info/error)
            since_offset: 从哪个字节偏移开始读取，None 或 0 表示从文件末尾往前读
            limit: 返回的最大行数
            
        Returns:
            LogQueryResult: 查询结果
        """
        limit = self._validate_limit(limit)
        log_file = self._get_log_file_path(log_type)
        
        # 检查日志文件是否存在
        if not log_file.exists():
            LOG.warning("日志文件不存在: %s", log_file)
            return LogQueryResult(
                lines=[],
                next_offset=0,
                total_lines=0,
                has_more=False
            )
        
        file_size = log_file.stat().st_size
        
        # 如果 since_offset 为空或 0，表示首次查询，从文件末尾往前读取最后 N 行
        if since_offset is None or since_offset == 0:
            return self._read_last_lines(log_file, limit, file_size)
        
        # 如果偏移量超出文件大小（可能是日志被轮转了），从头开始
        if since_offset > file_size:
            LOG.info("偏移量超出文件大小，可能日志已轮转，从头开始读取")
            since_offset = 0
        
        # 增量查询：从指定偏移量开始读取
        return self._read_from_offset(log_file, since_offset, limit, file_size)
    
    def _read_last_lines(
        self,
        log_file: Path,
        limit: int,
        file_size: int
    ) -> LogQueryResult:
        """
        从文件末尾读取最后 N 行
        
        Args:
            log_file: 日志文件路径
            limit: 最大行数
            file_size: 文件大小
            
        Returns:
            LogQueryResult: 查询结果
        """
        lines = []
        
        try:
            with open(log_file, 'rb') as f:
                # 使用一个缓冲区从末尾开始读取
                buffer_size = 8192
                buffer = b''
                position = file_size
                
                while len(lines) < limit and position > 0:
                    # 计算要读取的位置和大小
                    read_size = min(buffer_size, position)
                    position -= read_size
                    
                    f.seek(position)
                    chunk = f.read(read_size)
                    buffer = chunk + buffer
                    
                    # 按行分割
                    buffer_lines = buffer.split(b'\n')
                    
                    # 保留第一个不完整的行继续往前读
                    buffer = buffer_lines[0]
                    
                    # 添加完整的行（从后往前）
                    for line in reversed(buffer_lines[1:]):
                        if line.strip():  # 忽略空行
                            try:
                                lines.insert(0, line.decode('utf-8'))
                            except UnicodeDecodeError:
                                lines.insert(0, line.decode('utf-8', errors='replace'))
                            if len(lines) >= limit:
                                break
                
                # 处理最后剩余的 buffer（文件开头的内容）
                if len(lines) < limit and buffer.strip():
                    try:
                        lines.insert(0, buffer.decode('utf-8'))
                    except UnicodeDecodeError:
                        lines.insert(0, buffer.decode('utf-8', errors='replace'))
            
            # 只保留最后 limit 行
            lines = lines[-limit:]
            
            return LogQueryResult(
                lines=lines,
                next_offset=file_size,  # 下次从文件末尾开始查增量
                total_lines=len(lines),
                has_more=False  # 首次查询，后续增量通过轮询获取
            )
            
        except Exception as e:
            LOG.error("读取日志文件失败: %s, error: %s", log_file, e)
            return LogQueryResult(
                lines=[],
                next_offset=0,
                total_lines=0,
                has_more=False
            )
    
    def _read_from_offset(
        self,
        log_file: Path,
        offset: int,
        limit: int,
        file_size: int
    ) -> LogQueryResult:
        """
        从指定偏移量开始读取
        
        Args:
            log_file: 日志文件路径
            offset: 起始偏移量
            limit: 最大行数
            file_size: 文件大小
            
        Returns:
            LogQueryResult: 查询结果
        """
        lines = []
        next_offset = offset
        
        try:
            with open(log_file, 'rb') as f:
                f.seek(offset)
                
                line_count = 0
                while line_count < limit:
                    line = f.readline()
                    if not line:  # 到达文件末尾
                        break
                    
                    next_offset = f.tell()
                    
                    # 解码并添加到结果
                    line_str = line.rstrip(b'\n\r')
                    if line_str:  # 忽略空行
                        try:
                            lines.append(line_str.decode('utf-8'))
                        except UnicodeDecodeError:
                            lines.append(line_str.decode('utf-8', errors='replace'))
                        line_count += 1
                
                # 检查是否还有更多内容
                has_more = f.tell() < file_size
            
            return LogQueryResult(
                lines=lines,
                next_offset=next_offset,
                total_lines=len(lines),
                has_more=has_more
            )
            
        except Exception as e:
            LOG.error("读取日志文件失败: %s, error: %s", log_file, e)
            return LogQueryResult(
                lines=[],
                next_offset=offset,
                total_lines=0,
                has_more=False
            )
    
    def get_log_file_info(self, log_type: LogType) -> dict:
        """
        获取日志文件信息
        
        Args:
            log_type: 日志类型
            
        Returns:
            文件信息字典
        """
        log_file = self._get_log_file_path(log_type)
        
        if not log_file.exists():
            return {
                "exists": False,
                "path": str(log_file),
                "size": 0
            }
        
        stat = log_file.stat()
        return {
            "exists": True,
            "path": str(log_file),
            "size": stat.st_size,
            "modified_time": stat.st_mtime
        }


# 全局单例实例
_log_service: Optional[LogQueryService] = None


def get_log_service(logs_dir: Optional[str] = None) -> LogQueryService:
    """
    获取日志查询服务实例（单例）
    
    Args:
        logs_dir: 日志目录路径
        
    Returns:
        LogQueryService 实例
    """
    global _log_service
    if _log_service is None:
        _log_service = LogQueryService(logs_dir)
    return _log_service
