# -*- coding: utf-8 -*-
"""
Routes - 路由定义

定义所有 HTTP 接口路由。
"""

import logging

from fastapi import APIRouter, BackgroundTasks

from .deps import get_msg_handler, verify_token
from .exception_handlers import ApiResponse, ValidationException
from ..core import Config
from ..models import ChatMsg
from ..services import base_client
from ..services.listen_manager import get_listen_manager

LOG = logging.getLogger("Routes")

router = APIRouter()

# 获取 ListenManager 单例
listen_manager = get_listen_manager()


@router.get("/ping")
async def ping():
    """简单存活检查"""
    return "pong"


@router.get("/health")
async def health():
    """Docker 健康检查接口"""
    return {"status": "ok", "service": "true-love-server"}


@router.post("/send-msg")
async def send_msg(request: dict):
    """
    推送消息接口

    供外部调用，发送消息到指定接收者。
    """
    LOG.info("推送消息收到请求, req: %s", request)

    # 验证 token
    verify_token(request.get('token', ''))

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
    verify_token(request.get('token', ''))

    msg = ChatMsg.from_dict(request)
    msg_handler = get_msg_handler()

    # 使用后台任务异步处理消息
    background_tasks.add_task(msg_handler.handle_msg_async, msg)

    return ApiResponse(data="")


# ==================== Listen 监听管理接口 ====================

@router.get("/admin/listen/status")
async def get_listen_status():
    """
    获取监听状态
    
    状态定义（只有两种）：
    - healthy: 子窗口存在 AND ChatInfo 能正确响应
    - unhealthy: 子窗口不存在 OR ChatInfo 无法响应
    
    Returns:
        - listeners: 每个监听的状态列表
        - summary: 状态汇总 {"healthy": N, "unhealthy": M}
    """
    result = listen_manager.get_listener_status()
    return ApiResponse(data=result)


@router.post("/admin/listen/add")
async def add_listen(request: dict):
    """
    添加监听的聊天对象
    
    Request Body:
        - chat_name: 聊天对象名称（好友昵称或群名）
    """
    chat_name = request.get('chat_name', '')
    if not chat_name:
        raise ValidationException("chat_name 不能为空哦~")

    result = listen_manager.add_listen(chat_name)
    if not result.get("success"):
        raise ValidationException(result.get("message", "添加监听失败"))

    return ApiResponse(data=result)


@router.post("/admin/listen/remove")
async def remove_listen(request: dict):
    """
    移除监听的聊天对象
    
    Request Body:
        - chat_name: 聊天对象名称
    """
    chat_name = request.get('chat_name', '')
    if not chat_name:
        raise ValidationException("chat_name 不能为空哦~")

    result = listen_manager.remove_listen(chat_name)
    if not result.get("success"):
        raise ValidationException(result.get("message", "移除监听失败"))
    return ApiResponse(data=result)


@router.post("/admin/listen/refresh")
async def refresh_listen():
    """
    智能刷新监听列表
    
    流程：
    1. 获取监听状态
    2. healthy 的跳过，unhealthy 的执行 reset
    
    Returns:
        - total: 总监听数
        - success_count: 成功数
        - fail_count: 失败数
        - listeners: 每个监听的详情列表
    """
    result = listen_manager.refresh_listen()
    # refresh 返回的是统计结果，根据 fail_count 判断是否有失败
    if result.get("fail_count", 0) > 0:
        raise ValidationException(f"刷新部分失败: {result.get('fail_count')} 个监听恢复失败")
    return ApiResponse(data=result)


@router.post("/admin/listen/reset")
async def reset_listen(request: dict):
    """
    重置单个监听
    
    通过关闭子窗口、移除监听、重新添加监听的方式恢复异常的监听。
    
    Request Body:
        - chat_name: 聊天对象名称
        
    Returns:
        - success: 是否成功
        - message: 结果描述
        - steps: 各步骤执行情况
    """
    chat_name = request.get('chat_name', '')
    if not chat_name:
        raise ValidationException("chat_name 不能为空哦~")

    result = listen_manager.reset_listener(chat_name)
    if not result.get("success"):
        raise ValidationException(result.get("message", "重置监听失败"))
    return ApiResponse(data=result)


@router.post("/admin/listen/reset-all")
async def reset_all_listen():
    """
    重置所有监听
    
    通过停止所有监听、关闭所有子窗口、刷新 UI、重新添加所有监听的方式恢复。
    
    Returns:
        - success: 是否成功
        - message: 结果描述
        - total: 总监听数
        - recovered: 成功恢复的列表
        - failed: 恢复失败的列表
        - steps: 各步骤执行情况
    """
    result = listen_manager.reset_all_listeners()
    if not result.get("success"):
        raise ValidationException(result.get("message", "重置所有监听失败"))
    return ApiResponse(data=result)


@router.post("/admin/listen/get-all-message")
async def get_all_message(request: dict):
    """
    测活接口 - 获取聊天窗口的所有消息
    
    调用 Base 的 execute/chat 接口，执行 GetAllMessage 方法。
    
    Request Body:
        - chat_name: 聊天对象名称
        
    Returns:
        - success: 是否成功
        - data: 消息列表
        - message: 结果描述
    """
    chat_name = request.get('chat_name', '')
    if not chat_name:
        raise ValidationException("chat_name 不能为空哦~")

    result = base_client.execute_chat(chat_name, "GetAllMessage", {})
    if not result.get("success"):
        raise ValidationException(result.get("message", "获取消息失败"))
    return ApiResponse(data=result)
