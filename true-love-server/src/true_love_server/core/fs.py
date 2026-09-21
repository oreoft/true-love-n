# -*- coding: utf-8 -*-
"""
FS - 文件系统工具
"""

import os


def ensure_dir(path: str | os.PathLike) -> None:
    """
    确保目录存在，不存在则创建。

    Docker 部署时 /app 下的共享目录是指向 true-love-base 的软链，新机器上目标目录可能还没建。
    对悬空软链直接 mkdir 会抛 FileExistsError，所以先解析到真实路径再创建。
    """
    os.makedirs(os.path.realpath(path), exist_ok=True)
