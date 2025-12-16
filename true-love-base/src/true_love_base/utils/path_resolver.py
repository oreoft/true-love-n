# -*- coding: utf-8 -*-
"""
PathResolver - 路径解析工具

用于将 Server 发送的相对路径转换为 Base 可访问的完整路径。
往上级查找 true-love-n 作为项目根目录，再从中找到 true-love-server。
"""

import logging
import os

LOG = logging.getLogger("PathResolver")

# 项目根目录名
PROJECT_ROOT = "true-love-n"
# Server 目录名
SERVER_DIR = "true-love-server"


def _find_project_root() -> str:
    """
    往上级查找 true-love-n 目录
    
    Returns:
        项目根目录路径
    
    Raises:
        FileNotFoundError: 找不到项目根目录
    """
    current = os.getcwd()

    while True:
        if os.path.basename(current) == PROJECT_ROOT:
            return current

        parent = os.path.dirname(current)
        if parent == current:
            # 已经到根目录了
            raise FileNotFoundError(f"找不到项目根目录: {PROJECT_ROOT}")
        current = parent


def resolve_path(path: str) -> str:
    """
    解析路径，将 Server 的相对路径转换为完整路径
    
    Args:
        path: Server 发送的相对路径，如 "sd-img/xxx.png"
    
    Returns:
        完整路径
    
    Raises:
        FileNotFoundError: 文件不存在
    """
    if not path:
        return path

    # 如果已经是绝对路径，直接返回
    if os.path.isabs(path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"文件路径不存在: {path}")
        return path

    # 找到项目根目录 true-love-n
    project_root = _find_project_root()

    # 拼接 true-love-server 路径
    server_dir = os.path.join(project_root, SERVER_DIR)
    if not os.path.isdir(server_dir):
        raise FileNotFoundError(f"找不到 Server 目录: {server_dir}")

    # 拼接完整路径
    full_path = os.path.join(server_dir, path)

    if not os.path.exists(full_path):
        raise FileNotFoundError(f"文件路径不存在: {full_path}")

    LOG.info(f"Resolved path: {path} -> {full_path}")
    return full_path
