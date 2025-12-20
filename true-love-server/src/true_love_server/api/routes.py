# -*- coding: utf-8 -*-
"""
Routes - 路由定义

定义所有 HTTP 接口路由。
"""

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Query

from .exception_handlers import ApiResponse, AuthException, ValidationException
from .deps import get_msg_handler
from ..models import ChatMsg
from ..services import base_client
from ..services.log_service import LogType, get_log_service
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


@router.get("/logs")
async def query_logs(
    log_type: str = Query(default="info", description="日志类型: info 或 error"),
    limit: Optional[int] = Query(default=100, ge=1, le=500, description="返回行数，最大500"),
    since_offset: Optional[int] = Query(default=None, ge=0, description="从哪个字节偏移开始读取"),
):
    """
    查询日志接口
    
    支持增量查询，首次查询返回最后 N 行日志和 next_offset，
    后续查询带上 since_offset 获取新增内容。
    
    - **log_type**: 日志类型，可选 info 或 error
    - **limit**: 返回的最大行数，默认 100，最大 500
    - **since_offset**: 上次查询返回的 next_offset，首次查询不传或传 0
    
    Returns:
        - lines: 日志行列表
        - next_offset: 下次查询的偏移量
        - total_lines: 本次返回的行数
        - has_more: 是否还有更多内容
    """
    # 校验日志类型
    try:
        log_type_enum = LogType(log_type.lower())
    except ValueError:
        raise ValidationException(f"呜呜~不支持的日志类型哦: {log_type}，只能是 info 或 error 呢~")
    
    log_service = get_log_service()
    result = log_service.query_logs(
        log_type=log_type_enum,
        since_offset=since_offset,
        limit=limit
    )
    
    return ApiResponse(data={
        "lines": result.lines,
        "next_offset": result.next_offset,
        "total_lines": result.total_lines,
        "has_more": result.has_more
    })
