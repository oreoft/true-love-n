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
from ..services.listen_manager import get_listen_manager
from ..core import Config

LOG = logging.getLogger("Routes")

router = APIRouter()

# 获取 ListenManager 单例
listen_manager = get_listen_manager()


def _verify_token(token: str) -> bool:
    """验证 token"""
    http_config = Config().HTTP or {}
    valid_tokens = http_config.get("token", [])
    if token not in valid_tokens:
        raise AuthException("呜呜~身份验证失败了捏，token 不对哦~")
    return True


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
async def handle_logs(
    action: str = Query(default="query", description="操作类型: query 查询日志, truncate 清空日志"),
    log_type: str = Query(default="info", description="日志类型: info 或 error"),
    limit: Optional[int] = Query(default=100, ge=1, le=500, description="返回行数，最大500 (仅 query)"),
    since_offset: Optional[int] = Query(default=None, ge=0, description="从哪个字节偏移开始读取 (仅 query)"),
):
    """
    日志操作接口
    
    支持两种操作：
    - **query**: 查询日志，支持增量查询
    - **truncate**: 清空指定日志文件
    
    参数:
    - **action**: 操作类型，query 或 truncate
    - **log_type**: 日志类型，可选 info 或 error
    - **limit**: 返回的最大行数，默认 100，最大 500 (仅 query 有效)
    - **since_offset**: 上次查询返回的 next_offset (仅 query 有效)
    """
    # 校验日志类型
    try:
        log_type_enum = LogType(log_type.lower())
    except ValueError:
        raise ValidationException(f"呜呜~不支持的日志类型哦: {log_type}，只能是 info 或 error 呢~")
    
    log_service = get_log_service()
    action_lower = action.lower()
    
    if action_lower == "query":
        # 查询日志
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
    
    elif action_lower == "truncate":
        # 清空日志
        success = log_service.truncate_log(log_type_enum)
        if not success:
            raise ValidationException(f"呜呜~清空 {log_type} 日志失败了捏~")
        return ApiResponse(data={
            "message": f"{log_type} 日志已清空",
            "log_type": log_type
        })
    
    else:
        raise ValidationException(f"呜呜~不支持的操作类型哦: {action}，只能是 query 或 truncate 呢~")


# ==================== Listen 监听管理接口 ====================

@router.get("/listen/status")
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


@router.post("/listen/add")
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


@router.post("/listen/remove")
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
    return ApiResponse(data=result)


@router.post("/listen/refresh")
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
    return ApiResponse(data=result)


@router.post("/listen/reset")
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
    return ApiResponse(data=result)


@router.post("/listen/reset-all")
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
    return ApiResponse(data=result)
