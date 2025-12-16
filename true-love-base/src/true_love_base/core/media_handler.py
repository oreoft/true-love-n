# -*- coding: utf-8 -*-
"""
Media Handler - 媒体文件处理器

提供统一的媒体文件处理能力，包括：
- 下载管理
- 文件缓存
- 路径管理
"""

import logging
import os
import pathlib
import time
from datetime import datetime
from typing import Optional

LOG = logging.getLogger("MediaHandler")


class MediaHandler:
    """
    媒体文件处理器
    
    单例模式，提供统一的媒体文件管理能力。
    """
    _instance = None
    
    # 默认保存目录
    DEFAULT_SAVE_DIR = "files-save"
    
    def __new__(cls, save_dir: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super(MediaHandler, cls).__new__(cls)
            cls._instance._init_once(save_dir)
        return cls._instance
    
    def _init_once(self, save_dir: Optional[str] = None):
        """初始化（只执行一次）"""
        if hasattr(self, '_initialized'):
            return
        
        self.save_dir = save_dir or self.DEFAULT_SAVE_DIR
        self._ensure_dir(self.save_dir)
        self._initialized = True
        LOG.info(f"MediaHandler initialized, save_dir: {self.save_dir}")
    
    @staticmethod
    def _ensure_dir(dir_path: str) -> pathlib.Path:
        """确保目录存在"""
        path = pathlib.Path(dir_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_save_path(self, filename: str, subdir: Optional[str] = None) -> str:
        """
        获取保存文件的完整路径
        
        Args:
            filename: 文件名
            subdir: 子目录（可选）
            
        Returns:
            完整的文件路径
        """
        if subdir:
            dir_path = self._ensure_dir(os.path.join(self.save_dir, subdir))
        else:
            dir_path = self._ensure_dir(self.save_dir)
        return str((dir_path / filename).resolve())
    
    def generate_filename(self, prefix: str, extension: str) -> str:
        """
        生成带时间戳的文件名
        
        Args:
            prefix: 文件名前缀
            extension: 文件扩展名（不含点）
            
        Returns:
            生成的文件名
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.{extension}"
    
    def save_media(
        self,
        content: bytes,
        filename: str,
        subdir: Optional[str] = None
    ) -> Optional[str]:
        """
        保存媒体文件
        
        Args:
            content: 文件内容（二进制）
            filename: 文件名
            subdir: 子目录
            
        Returns:
            保存的文件路径，失败返回None
        """
        try:
            file_path = self.get_save_path(filename, subdir)
            with open(file_path, 'wb') as f:
                f.write(content)
            LOG.info(f"Media saved: {file_path}")
            return file_path
        except Exception as e:
            LOG.error(f"Failed to save media: {e}")
            return None
    
    def file_exists(self, filename: str, subdir: Optional[str] = None) -> Optional[str]:
        """
        检查文件是否存在
        
        Args:
            filename: 文件名
            subdir: 子目录
            
        Returns:
            如果存在返回完整路径，否则返回None
        """
        file_path = self.get_save_path(filename, subdir)
        if os.path.exists(file_path):
            return file_path
        return None
    
    def find_file_by_pattern(self, pattern: str, subdir: Optional[str] = None) -> Optional[str]:
        """
        按模式查找文件（用于检查是否已下载）
        
        Args:
            pattern: 文件名模式（支持通配符前缀匹配）
            subdir: 子目录
            
        Returns:
            找到的文件路径，否则返回None
        """
        if subdir:
            search_dir = self._ensure_dir(os.path.join(self.save_dir, subdir))
        else:
            search_dir = self._ensure_dir(self.save_dir)
        
        for file in search_dir.iterdir():
            if file.is_file() and file.name.startswith(pattern):
                return str(file.resolve())
        return None
    
    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """
        清理过期文件
        
        Args:
            max_age_hours: 最大保留时间（小时）
            
        Returns:
            删除的文件数量
        """
        deleted_count = 0
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        save_path = self._ensure_dir(self.save_dir)
        for file in save_path.rglob("*"):
            if file.is_file():
                file_age = current_time - file.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        file.unlink()
                        deleted_count += 1
                    except Exception as e:
                        LOG.warning(f"Failed to delete old file {file}: {e}")
        
        if deleted_count > 0:
            LOG.info(f"Cleaned up {deleted_count} old files")
        return deleted_count
