#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 路由模块
"""
import logging

from fastapi import APIRouter, Depends

from true_love_ai.api.deps import verify_token, get_chat_service, get_image_service, get_video_service
from true_love_ai.models.request import ChatRequest, ImageRequest, ImageTypeRequest, AnalyzeRequest, VideoRequest
from true_love_ai.models.response import APIResponse
from true_love_ai.services.chat_service import ChatService
from true_love_ai.services.image_service import ImageService
from true_love_ai.services.video_service import VideoService

LOG = logging.getLogger(__name__)

router = APIRouter()


@router.post("/get-llm")
async def get_llm(
        request: ChatRequest,
        service: ChatService = Depends(get_chat_service)
) -> APIResponse:
    """
    获取 LLM 回答
    
    支持意图识别：chat / search / gen-img
    自动管理对话历史
    
    可选参数：
    - provider: 指定模型提供商 (openai/claude/deepseek/gemini)
    - model: 指定具体模型
    """

    # 鉴权
    if not verify_token(request.token):
        return APIResponse.token_error()

    try:
        result = await service.get_answer(
            content=request.content,
            session_id=request.wxid or request.sender or "default",
            sender=request.sender,
            provider=request.provider,
            model=request.model
        )
        return APIResponse.success(result.model_dump(exclude_none=True))
    except Exception as e:
        LOG.exception(f"llm处理失败: {e}")
        return APIResponse.internal_error(str(e))


@router.post("/get-img-type")
async def get_img_type(
        request: ImageTypeRequest,
        service: ImageService = Depends(get_image_service)
) -> APIResponse:
    """
    判断图像操作类型
    
    返回类型：
    - gen_by_img: 图生图
    - erase_img: 擦除
    - replace_img: 替换
    - analyze_img: 分析
    - remove_background_img: 去背景
    """
    LOG.info(f"get-img-type消息收到请求, req: {str(request.model_dump())[:200]}")

    # 鉴权
    if not verify_token(request.token):
        return APIResponse.token_error()

    try:
        result = await service.get_img_type(
            content=request.content,
            provider=request.provider,
            model=request.model
        )
        return APIResponse.success(result)
    except Exception as e:
        LOG.exception(f"get-img-type处理失败: {e}")
        return APIResponse.internal_error(str(e))


@router.post("/gen-img")
async def gen_img(
        request: ImageRequest,
        service: ImageService = Depends(get_image_service)
) -> APIResponse:
    """
    生成图像
    
    - 文生图：只传 content
    - 图生图：传 content + img_data
    """
    LOG.info(f"gen-img消息收到请求, req: {str(request.model_dump())[:200]}")

    # 鉴权
    if not verify_token(request.token):
        return APIResponse.token_error()

    try:
        result = await service.generate_image(
            content=request.content,
            img_data=request.img_data,
            wxid=request.wxid,
            sender=request.sender,
            provider=request.provider,
            model=request.model
        )
        return APIResponse.success(result.model_dump(exclude_none=True))
    except Exception as e:
        LOG.exception(f"gen-img处理失败: {e}")
        return APIResponse.internal_error(str(e))


@router.post("/get-analyze")
async def get_analyze(
        request: AnalyzeRequest,
        service: ImageService = Depends(get_image_service)
) -> APIResponse:
    """
    分析图像内容
    """
    LOG.info(f"get-analyze消息收到请求, req: {str(request.model_dump())[:200]}")

    # 鉴权
    if not verify_token(request.token):
        return APIResponse.token_error()

    try:
        result = await service.analyze_image(
            content=request.content,
            img_data=request.img_data,
            wxid=request.wxid,
            sender=request.sender,
            provider=request.provider,
            model=request.model
        )
        return APIResponse.success(result)
    except Exception as e:
        LOG.exception(f"get-analyze处理失败: {e}")
        return APIResponse.internal_error(str(e))


@router.post("/gen-video")
async def gen_video(
        request: VideoRequest,
        service: VideoService = Depends(get_video_service)
) -> APIResponse:
    """
    生成视频
    
    - 文生视频：只传 content
    - 图生视频：传 content + img_data_list（图片数组）
    
    支持提供商：openai (Sora) / gemini (Veo)
    """
    LOG.info(f"gen-video消息收到请求, req: {str(request.model_dump())[:200]}")

    # 鉴权
    if not verify_token(request.token):
        return APIResponse.token_error()

    try:
        result = await service.generate_video(
            content=request.content,
            img_data_list=request.img_data_list,
            wxid=request.wxid,
            sender=request.sender,
            provider=request.provider,
            model=request.model
        )
        return APIResponse.success(result.model_dump(exclude_none=True))
    except Exception as e:
        LOG.exception(f"gen-video处理失败: {e}")
        return APIResponse.internal_error(str(e))
