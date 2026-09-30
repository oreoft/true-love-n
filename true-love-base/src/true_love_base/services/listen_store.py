# -*- coding: utf-8 -*-
"""
Listen Store - 监听列表持久化管理（只读）

Base 端只需要读取监听列表，写入操作由 Server 端负责。
文件位置：base 工作目录下的 listen_chats.json，server 通过 docker-compose 软链挂进容器
"""

import json
import logging
import os
import threading

LOG = logging.getLogger("ListenStore")


class ListenStore:
    """
    监听列表持久化管理（只读）
    
    Base 端简化版，只支持读取操作。
    写入操作由 Server 端的 ListenManager 负责。
    
    文件格式: ["chat_name1", "chat_name2", ...]
    """
    
    def __init__(self, file_path: str):
        """
        初始化 ListenStore（只读模式）
        
        Args:
            file_path: JSON 文件路径（base 工作目录下）
        """
        self._file_path = file_path
        self._lock = threading.Lock()
        
        LOG.info(f"ListenStore initialized (read-only): {file_path}")
    
    def _read_file(self) -> list[str]:
        """从文件读取监听列表"""
        try:
            if not os.path.exists(self._file_path):
                LOG.warning(f"Listen file not found: {self._file_path}")
                return []
            with open(self._file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return [str(item) for item in data]
                return []
        except json.JSONDecodeError as e:
            LOG.error(f"Failed to parse listen file: {e}")
            return []
        except Exception as e:
            LOG.error(f"Failed to read listen file: {e}")
            return []
    
    def load(self) -> list[str]:
        """
        加载监听列表
        
        每次调用都会重新读取文件，确保获取最新数据。
        
        Returns:
            监听对象名称列表
        """
        with self._lock:
            chats = self._read_file()
            LOG.info(f"Loaded {len(chats)} listen chats from file")
            return chats

