# -*- coding: utf-8 -*-
"""
PathResolver - 路径解析工具

Base 端文件路径处理工具。

设计原则：
- 共享文件统一存储在 Base 工作目录下（wx_imgs/、moyu-jpg/、zaobao-jpg/ 等）
- Server 通过 Docker 挂载映射来读取 Base 目录的文件
- 传输给 Server 时：使用相对路径（如 wx_imgs/filename.jpg）
- uv 执行时工作目录就是 true-love-base，直接使用相对路径即可

核心函数：
- get_listen_chats_file(): 获取 listen_chats.json 路径
- get_wx_imgs_dir(): 获取 wx_imgs 路径，用于 Base 下载文件
- to_server_path(): 将完整路径转为相对路径，用于传输给 Server
- resolve_path(): 解析相对路径，用于 Base 读取文件
"""

import logging
import os

LOG = logging.getLogger("PathResolver")

# 微信图片下载目录名
WX_IMGS_DIR = "wx_imgs"


def get_listen_chats_file() -> str:
    """
    获取 listen_chats.json 文件路径
    
    Returns:
        listen_chats.json 的路径
    """
    return "listen_chats.json"


def get_wx_imgs_dir() -> str:
    """
    获取 wx_imgs 文件夹路径
    
    如果文件夹不存在则创建。
    用于 Base 下载微信图片，Server 通过 Docker 挂载读取。
    
    Returns:
        wx_imgs 文件夹路径
    """
    if not os.path.exists(WX_IMGS_DIR):
        os.makedirs(WX_IMGS_DIR)
        LOG.info(f"Created wx_imgs directory: {WX_IMGS_DIR}")
    
    return WX_IMGS_DIR


def to_server_path(full_path: str, subdir: str = WX_IMGS_DIR) -> str:
    """
    将完整路径转换为 Server 可用的相对路径
    
    用于 Base 下载文件后，将路径转换为传输给 Server 的格式。
    
    Args:
        full_path: 完整文件路径，如 "wx_imgs/xxx.jpg"
        subdir: 子目录名，默认为 wx_imgs
    
    Returns:
        相对路径，如 "wx_imgs/xxx.jpg"
    
    Example:
        >>> to_server_path("wx_imgs/image.jpg")
        "wx_imgs/image.jpg"
    """
    if not full_path:
        return None

    # 提取文件名
    filename = os.path.basename(str(full_path))
    # 返回相对路径
    relative_path = f"{subdir}/{filename}"
    LOG.debug(f"Converted to server path: {full_path} -> {relative_path}")
    return relative_path


def resolve_path(path: str) -> str:
    """
    解析文件路径，确保文件存在
    
    用于 Base 读取 Server 发送的文件路径。
    
    Args:
        path: 相对路径，如 "wx_imgs/xxx.png" 或 "moyu-jpg/xxx.jpg"
    
    Returns:
        文件路径（验证存在后返回）
    
    Raises:
        FileNotFoundError: 文件不存在
    
    Example:
        >>> resolve_path("moyu-jpg/12-28.jpg")
        "moyu-jpg/12-28.jpg"
    """
    if not path:
        return path

    # 检查文件是否存在
    if not os.path.exists(path):
        raise FileNotFoundError(f"文件路径不存在: {path}")

    LOG.debug(f"Resolved path: {path}")
    return path
