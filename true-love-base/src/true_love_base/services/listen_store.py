# -*- coding: utf-8 -*-
"""
Listen Store - 监听列表持久化管理

负责监听对象列表的持久化存储，支持增删查操作。
"""

import json
import logging
import os
import threading
from typing import Optional

LOG = logging.getLogger("ListenStore")


class ListenStore:
    """
    监听列表持久化管理
    
    将监听对象存储到 JSON 文件中，支持动态增删查。
    文件格式: ["chat_name1", "chat_name2", ...]
    """
    
    def __init__(self, file_path: str):
        """
        初始化 ListenStore
        
        Args:
            file_path: JSON 文件路径
        """
        self._file_path = file_path
        self._lock = threading.Lock()
        self._cache: Optional[list[str]] = None
        
        LOG.info(f"ListenStore initialized with file: {file_path}")
    
    def _ensure_file_exists(self) -> None:
        """确保文件存在，不存在则创建空列表"""
        if not os.path.exists(self._file_path):
            dir_path = os.path.dirname(self._file_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)
            self._write_file([])
            LOG.info(f"Created empty listen file: {self._file_path}")
    
    def _read_file(self) -> list[str]:
        """从文件读取监听列表"""
        try:
            if not os.path.exists(self._file_path):
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
    
    def _write_file(self, chats: list[str]) -> bool:
        """
        写入监听列表到文件
        
        使用临时文件 + rename 方式保证原子性
        """
        try:
            temp_path = self._file_path + ".tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(chats, f, ensure_ascii=False, indent=2)
            
            # 原子性替换
            os.replace(temp_path, self._file_path)
            return True
        except Exception as e:
            LOG.error(f"Failed to write listen file: {e}")
            # 清理临时文件
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            return False
    
    def load(self) -> list[str]:
        """
        加载监听列表
        
        Returns:
            监听对象名称列表
        """
        with self._lock:
            self._cache = self._read_file()
            LOG.info(f"Loaded {len(self._cache)} listen chats from file")
            return self._cache.copy()
    
    def save(self, chats: list[str]) -> bool:
        """
        保存监听列表
        
        Args:
            chats: 监听对象名称列表
            
        Returns:
            是否保存成功
        """
        with self._lock:
            success = self._write_file(chats)
            if success:
                self._cache = chats.copy()
            return success
    
    def list_all(self) -> list[str]:
        """
        获取所有监听对象
        
        Returns:
            监听对象名称列表
        """
        with self._lock:
            if self._cache is None:
                self._cache = self._read_file()
            return self._cache.copy()
    
    def add(self, chat_name: str) -> bool:
        """
        添加监听对象
        
        Args:
            chat_name: 聊天对象名称
            
        Returns:
            是否新增成功（已存在返回 False）
        """
        with self._lock:
            if self._cache is None:
                self._cache = self._read_file()
            
            if chat_name in self._cache:
                LOG.info(f"Chat [{chat_name}] already in listen list")
                return False
            
            self._cache.append(chat_name)
            success = self._write_file(self._cache)
            if success:
                LOG.info(f"Added [{chat_name}] to listen list")
            else:
                # 回滚缓存
                self._cache.remove(chat_name)
            return success
    
    def remove(self, chat_name: str) -> bool:
        """
        移除监听对象
        
        Args:
            chat_name: 聊天对象名称
            
        Returns:
            是否移除成功（不存在返回 False）
        """
        with self._lock:
            if self._cache is None:
                self._cache = self._read_file()
            
            if chat_name not in self._cache:
                LOG.info(f"Chat [{chat_name}] not in listen list")
                return False
            
            self._cache.remove(chat_name)
            success = self._write_file(self._cache)
            if success:
                LOG.info(f"Removed [{chat_name}] from listen list")
            else:
                # 回滚缓存
                self._cache.append(chat_name)
            return success
    
    def exists(self, chat_name: str) -> bool:
        """
        检查监听对象是否存在
        
        Args:
            chat_name: 聊天对象名称
            
        Returns:
            是否存在
        """
        with self._lock:
            if self._cache is None:
                self._cache = self._read_file()
            return chat_name in self._cache
