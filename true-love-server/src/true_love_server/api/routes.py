# -*- coding: utf-8 -*-
"""
Routes - 路由定义

定义所有 HTTP 接口路由。
"""

import logging

from fastapi import APIRouter, BackgroundTasks

from .exception_handlers import ApiResponse, AuthException, ValidationException
from .deps import get_msg_handler
from ..models import ChatMsg
from ..services import base_client
from ..core import Config

LOG = logging.getLogger("Routes")

router = APIRouter()


def _verify_token(token: str) -> bool:
    """验证 token"""
    http_config = Config().HTTP or {}
    valid_tokens = http_config.get("token", [])
    if token not in valid_tokens:
        raise AuthException("呜呜~身份验证失败了捏，token 不对哦~")
    return True


@router.get("/")
async def root():
    """健康检查"""
    return "pong"


@router.get("/ping")
async def ping():
    """健康检查"""
    return "pong"


@router.post("/send-msg")
async def send_msg(request: dict):
    """
    推送消息接口

    供外部调用，发送消息到指定接收者。
    """
    LOG.info("推送消息收到请求, req: %s", request)

    # 验证 token
    _verify_token(request.get('token', ''))

    http_config = Config().HTTP or {}
    send_receiver = request.get('sendReceiver')
    at_receiver = request.get('atReceiver')
    content = request.get('content')
    receiver_map = http_config.get("receiver_map", {})

    # 判断是否合法发送人
    if not receiver_map.get(send_receiver) or not content:
        raise ValidationException("诶嘿~接收者没注册或者内容是空的呢，检查一下吧~")

    # 开始发送（同步接口，失败需要返回错误）
    success, error_msg = base_client.send_text(
        receiver_map.get(send_receiver, ""),
        receiver_map.get(at_receiver, ""),
        content
    )

    if not success:
        raise ValidationException(f"呜呜~消息发送失败了捏: {error_msg}")

    return ApiResponse(data=None)


@router.post("/get-chat")
async def get_chat(
    request: dict,
    background_tasks: BackgroundTasks,
):
    """
    聊天消息接口

    接收消息并处理，返回回复内容。
    """
    LOG.info("聊天消息收到请求, req: %s", request)

    # 验证 token
    _verify_token(request.get('token', ''))

    msg = ChatMsg.from_dict(request)
    msg_handler = get_msg_handler()

    # 使用后台任务异步处理消息
    background_tasks.add_task(msg_handler.handle_msg_async, msg)

    return ApiResponse(data="")
