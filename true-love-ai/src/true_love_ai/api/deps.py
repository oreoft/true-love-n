#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖注入模块
"""
from true_love_ai.core.config import get_config
from true_love_ai.services.chat_service import ChatService
from true_love_ai.services.image_service import ImageService
from true_love_ai.services.video_service import VideoService


def verify_token(token: str) -> bool:
    """验证 Token"""
    config = get_config()
    if config.http is None:
        return False
    return token in config.http.token


def get_chat_service() -> ChatService:
    """获取聊天服务"""
    return ChatService()


def get_image_service() -> ImageService:
    """获取图像服务"""
    return ImageService()


def get_video_service() -> VideoService:
    """获取视频服务"""
    return VideoService()
