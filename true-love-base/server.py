# -*- coding: utf-8 -*-
"""
HTTP Server - 提供 HTTP API 服务

提供外部调用接口，用于发送消息等操作。
"""

import logging
import time
from threading import Thread
from typing import Optional

from flask import Flask, g, request, jsonify

from robot import Robot
from models.api import ApiResponse, ApiErrors

app = Flask(__name__)
LOG = logging.getLogger("Server")

# 全局 Robot 实例
_robot: Optional[Robot] = None


def get_robot() -> Optional[Robot]:
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
        - path: 图片路径
    """
    robot = get_robot()
    if robot is None:
        return jsonify(ApiErrors.ROBOT_NOT_READY.to_dict())
    
    data = request.json or {}
    path = data.get('path', '')
    receiver = data.get('sendReceiver', '')
    
    if not receiver or not path:
        return jsonify(ApiErrors.INVALID_PARAMS.to_dict())
    
    success = robot.send_img_msg(path, receiver)
    
    if success:
        return jsonify(ApiResponse.success().to_dict())
    return jsonify(ApiErrors.SEND_FAILED.to_dict())


@app.route('/send/file', methods=['POST'])
def send_file():
    """
    发送文件
    
    Request Body:
        - sendReceiver: 接收者
        - path: 文件路径
    """
    robot = get_robot()
    if robot is None:
        return jsonify(ApiErrors.ROBOT_NOT_READY.to_dict())
    
    data = request.json or {}
    path = data.get('path', '')
    receiver = data.get('sendReceiver', '')
    
    if not receiver or not path:
        return jsonify(ApiErrors.INVALID_PARAMS.to_dict())
    
    success = robot.send_file_msg(path, receiver)
    
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

def enable_http(robot: Robot, host: str = "0.0.0.0", port: int = 5000):
    """
    启动 HTTP 服务
    
    Args:
        robot: Robot 实例
        host: 绑定地址
        port: 端口
    """
    global _robot
    _robot = robot
    
    Thread(
        target=app.run,
        name="HttpServer",
        kwargs={"host": host, "port": port, "threaded": True},
        daemon=True,
    ).start()
    
    LOG.info(f"HTTP server started on {host}:{port}")


if __name__ == '__main__':
    app.run(debug=True)
