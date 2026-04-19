#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 路由模块 — 文件下载接口（供 Server 拉取 AI 生成的图片/视频）
消息处理已全部由 AgentLoop 接管，通过 /trigger 入口。
"""
import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from true_love_ai.api.deps import verify_token
from true_love_ai.services.image_service import GEN_IMG_DIR
from true_love_ai.services.video_service import GEN_VIDEO_DIR

LOG = logging.getLogger(__name__)

router = APIRouter()


@router.get("/download-image/{file_id}")
async def download_image(
        file_id: str,
        token: str = Query(..., description="鉴权 Token")
) -> FileResponse:
    """下载 AI 生成的图片（供 Server 拉取后转发给 Base）"""
    if not verify_token(token):
        raise HTTPException(status_code=403, detail="Token 验证失败")

    img_path = GEN_IMG_DIR / f"{file_id}.jpg"
    if not img_path.exists():
        raise HTTPException(status_code=404, detail="图片不存在或已过期")

    return FileResponse(path=img_path, media_type="image/jpeg", filename=f"{file_id}.jpg")


@router.get("/download-video/{video_id}")
async def download_video(
        video_id: str,
        token: str = Query(..., description="鉴权 Token")
) -> FileResponse:
    """下载 AI 生成的视频（供 Server 拉取后转发给 Base）"""
    LOG.info("download-video 请求, video_id: %s", video_id)

    if not verify_token(token):
        raise HTTPException(status_code=403, detail="Token 验证失败")

    video_path = GEN_VIDEO_DIR / f"{video_id}.mp4"
    if not video_path.exists():
        LOG.warning("视频文件不存在: %s", video_path)
        raise HTTPException(status_code=404, detail="视频文件不存在或已过期")

    return FileResponse(path=video_path, media_type="video/mp4", filename=f"{video_id}.mp4")
