# -*- coding: utf-8 -*-
"""
HTTP Server - 提供 HTTP API 服务

提供外部调用接口，用于发送消息等操作。
使用 Waitress 作为生产级 WSGI 服务器。
"""

import logging
import time
from threading import Thread
from typing import Optional, TYPE_CHECKING

from flask import Flask, g, request, jsonify
from waitress import serve

from true_love_base.models.api import ApiResponse, ApiErrors
from true_love_base.utils.path_resolver import resolve_path

if TYPE_CHECKING:
    from true_love_base.services.robot import Robot

app = Flask(__name__)
LOG = logging.getLogger("Server")

# 全局 Robot 实例
_robot: Optional["Robot"] = None


def get_robot() -> Optional["Robot"]:
    """获取 Robot 实例"""
    return _robot


# ==================== API Routes ====================

@app.route('/')
def root():
    """健康检查"""
    return "pong"


@app.route('/ping')
def ping():
    """健康检查"""
    return "pong"


@app.route('/send/text', methods=['POST'])
def send_text():
    """
    发送文本消息
    
    Request Body:
        - sendReceiver: 接收者
        - content: 消息内容
        - atReceiver: 要@的人（可选）
    """
    robot = get_robot()
    if robot is None:
        return jsonify(ApiErrors.ROBOT_NOT_READY.to_dict())
    
    data = request.json or {}
    receiver = data.get('sendReceiver', '')
    content = data.get('content', '')
    at_receiver = data.get('atReceiver', '')
    
    if not receiver or not content:
        return jsonify(ApiErrors.INVALID_PARAMS.to_dict())
    
    success = robot.send_text_msg(content, receiver, at_receiver if at_receiver else None)
    
    if success:
        return jsonify(ApiResponse.success().to_dict())
    return jsonify(ApiErrors.SEND_FAILED.to_dict())


@app.route('/send/img', methods=['POST'])
def send_img():
    """
    发送图片消息
    
    Request Body:
        - sendReceiver: 接收者
        - path: 图片路径（可以是 Server 的相对路径，会自动在 true-love-server 目录下查找）
    """
    robot = get_robot()
    if robot is None:
        return jsonify(ApiErrors.ROBOT_NOT_READY.to_dict())
    
    data = request.json or {}
    path = data.get('path', '')
    receiver = data.get('sendReceiver', '')
    
    if not receiver or not path:
        return jsonify(ApiErrors.INVALID_PARAMS.to_dict())
    
    # 解析 Server 相对路径
    try:
        resolved_path = resolve_path(path)
    except FileNotFoundError as e:
        LOG.error(f"Failed to send image to [{receiver}]: {e}")
        return jsonify(ApiErrors.SEND_FAILED.to_dict())
    
    success = robot.send_img_msg(resolved_path, receiver)
    
    if success:
        return jsonify(ApiResponse.success().to_dict())
    return jsonify(ApiErrors.SEND_FAILED.to_dict())


@app.route('/send/file', methods=['POST'])
def send_file():
    """
    发送文件
    
    Request Body:
        - sendReceiver: 接收者
        - path: 文件路径（可以是 Server 的相对路径，会自动在 true-love-server 目录下查找）
    """
    robot = get_robot()
    if robot is None:
        return jsonify(ApiErrors.ROBOT_NOT_READY.to_dict())
    
    data = request.json or {}
    path = data.get('path', '')
    receiver = data.get('sendReceiver', '')
    
    if not receiver or not path:
        return jsonify(ApiErrors.INVALID_PARAMS.to_dict())
    
    # 解析 Server 相对路径
    try:
        resolved_path = resolve_path(path)
    except FileNotFoundError as e:
        LOG.error(f"Failed to send file to [{receiver}]: {e}")
        return jsonify(ApiErrors.SEND_FAILED.to_dict())
    
    success = robot.send_file_msg(resolved_path, receiver)
    
    if success:
        return jsonify(ApiResponse.success().to_dict())
    return jsonify(ApiErrors.SEND_FAILED.to_dict())


@app.route('/get/all', methods=['GET'])
def get_all_contacts():
    """
    获取所有联系人
    
    Note: wxautox4 可能不支持此功能
    """
    robot = get_robot()
    if robot is None:
        return jsonify(ApiErrors.ROBOT_NOT_READY.to_dict())
    
    contacts = robot.get_all_contacts()
    return jsonify(ApiResponse.success(contacts).to_dict())


@app.route('/get/by/room-id', methods=['POST'])
def get_contacts_by_room_id():
    """
    获取群成员
    
    Request Body:
        - room_id: 群名称
        
    Note: wxautox4 可能不支持此功能
    """
    robot = get_robot()
    if robot is None:
        return jsonify(ApiErrors.ROBOT_NOT_READY.to_dict())
    
    data = request.json or {}
    room_id = data.get('room_id', '')
    
    if not room_id:
        return jsonify(ApiErrors.INVALID_PARAMS.to_dict())
    
    members = robot.get_contacts_by_chat_name(room_id)
    return jsonify(ApiResponse.success(members).to_dict())


@app.route('/listen/list', methods=['GET'])
def list_listen_chats():
    """
    获取所有监听对象
    
    Response:
        - data: 监听对象名称列表
    """
    robot = get_robot()
    if robot is None:
        return jsonify(ApiErrors.ROBOT_NOT_READY.to_dict())
    
    chats = robot.get_listen_chats()
    return jsonify(ApiResponse.success(chats).to_dict())


@app.route('/listen/add', methods=['POST'])
def add_listen_chat():
    """
    添加监听的聊天对象
    
    Request Body:
        - chat_name: 聊天对象名称（好友昵称或群名）
    """
    robot = get_robot()
    if robot is None:
        return jsonify(ApiErrors.ROBOT_NOT_READY.to_dict())
    
    data = request.json or {}
    chat_name = data.get('chat_name', '')
    
    if not chat_name:
        return jsonify(ApiErrors.INVALID_PARAMS.to_dict())
    
    success = robot.add_listen_chat(chat_name)
    
    if success:
        return jsonify(ApiResponse.success().to_dict())
    return jsonify(ApiResponse.error(104, "Failed to add listener").to_dict())


@app.route('/listen/remove', methods=['POST'])
def remove_listen_chat():
    """
    移除监听的聊天对象
    
    Request Body:
        - chat_name: 聊天对象名称
    """
    robot = get_robot()
    if robot is None:
        return jsonify(ApiErrors.ROBOT_NOT_READY.to_dict())
    
    data = request.json or {}
    chat_name = data.get('chat_name', '')
    
    if not chat_name:
        return jsonify(ApiErrors.INVALID_PARAMS.to_dict())
    
    success = robot.remove_listen_chat(chat_name)
    
    if success:
        return jsonify(ApiResponse.success().to_dict())
    return jsonify(ApiResponse.error(105, "Failed to remove listener").to_dict())


@app.route('/listen/refresh', methods=['POST'])
def refresh_listen_chats():
    """
    刷新监听列表
    
    比对内存和文件中的监听列表，重新添加缺失的监听。
    用于修复因窗口句柄失效等原因导致的监听丢失问题。
    
    Response:
        - data: 刷新结果，包含 file_chats, memory_chats, missing, extra, recovered, failed
    """
    robot = get_robot()
    if robot is None:
        return jsonify(ApiErrors.ROBOT_NOT_READY.to_dict())
    
    result = robot.refresh_listen_chats()
    return jsonify(ApiResponse.success(result).to_dict())


@app.route('/listen/reset', methods=['POST'])
def reset_listener():
    """
    重置单个监听
    
    通过关闭子窗口、移除监听、重新添加监听的方式恢复异常的监听。
    用于修复因 UIA 窗口异常导致的单个监听失效问题。
    
    Request Body:
        - chat_name: 聊天对象名称
        
    Response:
        - data: 重置结果，包含 success, message, steps
    """
    robot = get_robot()
    if robot is None:
        return jsonify(ApiErrors.ROBOT_NOT_READY.to_dict())
    
    data = request.json or {}
    chat_name = data.get('chat_name', '')
    
    if not chat_name:
        return jsonify(ApiErrors.INVALID_PARAMS.to_dict())
    
    result = robot.reset_listener(chat_name)
    return jsonify(ApiResponse.success(result).to_dict())


@app.route('/listen/reset-all', methods=['POST'])
def reset_all_listeners():
    """
    重置所有监听
    
    通过停止所有监听、关闭所有子窗口、切换页面刷新 UI、重新添加所有监听的方式恢复。
    用于修复因 UIA 整体异常导致的全部监听失效问题。
    
    Response:
        - data: 重置结果，包含 success, message, total, recovered, failed, steps
    """
    robot = get_robot()
    if robot is None:
        return jsonify(ApiErrors.ROBOT_NOT_READY.to_dict())
    
    result = robot.reset_all_listeners()
    return jsonify(ApiResponse.success(result).to_dict())


@app.route('/listen/health', methods=['GET'])
def listener_health_check():
    """
    监听健康检查
    
    通过比对已注册的监听和实际活跃的子窗口来判断监听是否健康。
    外部服务可定时调用此接口检测监听状态。
    
    Response:
        - data: 健康检查结果，包含:
            - healthy: 是否健康
            - message: 状态描述
            - registered_listeners: 已注册的监听列表
            - active_windows: 活跃的子窗口列表
            - unhealthy_listeners: 异常的监听列表
            - orphan_windows: 孤立的窗口列表
    """
    robot = get_robot()
    if robot is None:
        return jsonify(ApiErrors.ROBOT_NOT_READY.to_dict())
    
    result = robot.listener_health_check()
    return jsonify(ApiResponse.success(result).to_dict())


# ==================== Middleware ====================

@app.before_request
def before_request_logging():
    """请求前日志"""
    g.start_time = time.time()
    body = request.get_data(as_text=True)
    LOG.info(f"Request: [{request.method} {request.path}], body: {body[:200]}")


@app.after_request
def after_request_logging(response):
    """请求后日志"""
    cost = (time.time() - g.start_time) * 1000
    body = response.get_data(as_text=True)
    LOG.info(f"Response: [{request.method} {request.path}], cost: {cost:.0f}ms, body: {body[:200]}")
    return response


# ==================== Server Control ====================

# Waitress 配置
WAITRESS_THREADS = 8  # 工作线程数
WAITRESS_CHANNEL_TIMEOUT = 120  # 通道超时（秒）


def enable_http(robot: "Robot", host: str = "0.0.0.0", port: int = 5000):
    """
    启动 HTTP 服务（使用 Waitress 生产级服务器）
    
    Args:
        robot: Robot 实例
        host: 绑定地址
        port: 端口
    """
    global _robot
    _robot = robot
    
    def run_server():
        """运行 Waitress 服务器"""
        serve(
            app,
            host=host,
            port=port,
            threads=WAITRESS_THREADS,
            channel_timeout=WAITRESS_CHANNEL_TIMEOUT,
            _quiet=True,  # 禁用 Waitress 默认日志，使用我们自己的
        )
    
    t = Thread(
        target=run_server,
        name="HttpServer",
        daemon=True,  # 守护线程，主线程退出时自动结束
    )
    t.start()
    
    LOG.info(f"HTTP server (Waitress) started on {host}:{port}, threads={WAITRESS_THREADS}")


if __name__ == '__main__':
    # 开发模式使用 Flask 内置服务器
    app.run(debug=True)
