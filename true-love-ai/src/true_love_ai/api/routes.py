#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 路由模块 — 媒体文件服务接口（供 Server 拉取 AI 生成的图片/视频/文件）
消息处理已全部由 AgentLoop 接管，通过 /trigger 入口。
"""
import logging
import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from true_love_ai.services.image_service import GEN_IMG_DIR
from true_love_ai.services.video_service import GEN_VIDEO_DIR

LOG = logging.getLogger(__name__)

router = APIRouter()

# 允许对外服务的根目录白名单（防止路径穿越）
_ALLOWED_DIRS: dict[str, Path] = {
    GEN_IMG_DIR.name: GEN_IMG_DIR,
    GEN_VIDEO_DIR.name: GEN_VIDEO_DIR,
}


@router.get("/media/{path:path}")
async def serve_media(path: str) -> FileResponse:
    """
    统一媒体文件服务接口（供 Server 拉取 AI 生成的任意文件）

    path 格式：{dir}/{filename}，如 gen_img/abc123.jpg、gen_video/abc123.mp4
    文件名为 UUID，路径本身即是访问凭证，无需额外 token。
    """
    parts = path.lstrip("/").split("/", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="path 格式错误，应为 {dir}/{filename}")

    dir_name, filename = parts

    base_dir = _ALLOWED_DIRS.get(dir_name)
    if base_dir is None:
        raise HTTPException(status_code=404, detail=f"目录不存在: {dir_name}")

    # 防止路径穿越
    file_path = (base_dir / filename).resolve()
    if not str(file_path).startswith(str(base_dir.resolve())):
        raise HTTPException(status_code=403, detail="非法路径")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在或已过期")

    mime_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(
        path=file_path,
        media_type=mime_type or "application/octet-stream",
        filename=filename,
    )
