# -*- coding: utf-8 -*-
"""
PathResolver - 路径解析工具

Base 端文件路径处理工具，用于 Base(Windows) 和 Server(WSL) 之间的文件路径交换。

设计原则：
- 文件统一存储在 Server 目录下（如 true-love-server/wx_imgs/）
- Base 下载/生成文件时：找到 Server 目录 → 写入
- Base 读取文件时：找到 Server 目录 → 读取
- 传输给 Server 时：使用相对路径（如 wx_imgs/filename.jpg）
- Server 直接使用相对路径

核心函数：
- get_wx_imgs_dir(): 获取 wx_imgs 完整路径，用于 Base 下载文件
- to_server_path(): 将完整路径转为相对路径，用于传输给 Server
- resolve_path(): 将相对路径转为完整路径，用于 Base 读取文件
"""

import logging
import os

LOG = logging.getLogger("PathResolver")

# 项目根目录名
PROJECT_ROOT = "true-love-n"
# Server 目录名
SERVER_DIR = "true-love-server"
# 微信图片下载目录名
WX_IMGS_DIR = "wx_imgs"


def _find_project_root() -> str:
    """
    通过当前文件路径查找 true-love-n 目录
    
    路径结构: true-love-n/true-love-base/src/true_love_base/utils/path_resolver.py
    从当前文件往上 5 层就是项目根目录
    
    Returns:
        项目根目录路径
    
    Raises:
        FileNotFoundError: 找不到项目根目录
    """
    # 使用 __file__ 定位，比 os.getcwd() 更可靠
    current = os.path.dirname(os.path.abspath(__file__))

    # 往上查找 true-love-n 目录
    for _ in range(10):  # 最多查找 10 层
        if os.path.basename(current) == PROJECT_ROOT:
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    raise FileNotFoundError(f"找不到项目根目录: {PROJECT_ROOT}")


def get_listen_chats_file():
    try:
        return os.path.join(_find_project_root(), SERVER_DIR, "listen_chats.json")
    except FileNotFoundError:
        # 降级：使用当前目录（兼容旧配置）
        return "listen_chats.json"


def get_wx_imgs_dir() -> str:
    """
    获取 server 目录下的 wx_imgs 文件夹路径
    
    如果文件夹不存在则创建。
    用于 base 下载微信图片，server 可以直接读取。
    
    Returns:
        wx_imgs 文件夹的绝对路径
    """
    try:
        project_root = _find_project_root()
        LOG.info(f"Project root: {project_root}")
        wx_imgs_path = os.path.join(project_root, SERVER_DIR, WX_IMGS_DIR)
        LOG.info(f"wx_imgs_path: {wx_imgs_path}")

        # 如果目录不存在，创建它
        if not os.path.exists(wx_imgs_path):
            os.makedirs(wx_imgs_path)
            LOG.info(f"Created wx_imgs directory: {wx_imgs_path}")

        return wx_imgs_path
    except FileNotFoundError as e:
        LOG.warning(f"Failed to get wx_imgs dir: {e}")
        # 返回 None 让调用方使用默认路径
        return None


def to_server_path(full_path: str, subdir: str = WX_IMGS_DIR) -> str:
    """
    将完整路径转换为 Server 可用的相对路径
    
    用于 Base 下载文件后，将路径转换为传输给 Server 的格式。
    
    Args:
        full_path: 完整文件路径，如 "/path/to/true-love-server/wx_imgs/xxx.jpg"
        subdir: 子目录名，默认为 wx_imgs
    
    Returns:
        相对路径，如 "wx_imgs/xxx.jpg"
    
    Example:
        >>> to_server_path("/path/to/server/wx_imgs/image.jpg")
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
    将 Server 的相对路径转换为 Base 可访问的完整路径
    
    用于 Base 读取 Server 发送的文件路径。
    
    Args:
        path: Server 发送的相对路径，如 "wx_imgs/xxx.png" 或 "sd-img/xxx.png"
    
    Returns:
        完整路径
    
    Raises:
        FileNotFoundError: 文件不存在
    
    Example:
        >>> resolve_path("wx_imgs/image.jpg")
        "/path/to/true-love-server/wx_imgs/image.jpg"
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

    LOG.debug(f"Resolved path: {path} -> {full_path}")
    return full_path
