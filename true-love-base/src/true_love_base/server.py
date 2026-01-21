# -*- coding: utf-8 -*-
"""
HTTP Server - 提供 HTTP API 服务

提供外部调用接口，用于发送消息等操作。
使用 Waitress 作为生产级 WSGI 服务器。
"""

import json
import logging
import random

import time
from threading import Thread
from typing import Optional, TYPE_CHECKING, Any

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


# ==================== 通用执行接口配置 ====================

# 方法黑名单 - 禁止调用的方法
METHOD_BLACKLIST = {
    'ShutDown',  # 危险：会杀掉微信进程
    'KeepRunning',  # 阻塞方法，不应通过 API 调用
    'StartListening',  # 阻塞方法
    'StopListening',  # 可能影响正常监听
    'AddListenChat',  # 需要 callback，使用 /listen/add 独立接口
}


def is_method_allowed(method_name: str) -> bool:
    """
    检查方法是否允许调用
    
    Args:
        method_name: 方法名
        
    Returns:
        是否允许调用
    """
    # 过滤 __ 开头的系统方法
    if method_name.startswith('__'):
        return False
    # 过滤 _ 开头的私有方法
    if method_name.startswith('_'):
        return False
    # 过滤黑名单
    if method_name in METHOD_BLACKLIST:
        return False
    return True


def serialize_result(result: Any) -> Any:
    """
    通用序列化返回值
    
    Args:
        result: 方法返回值
        
    Returns:
        可 JSON 序列化的结果
    """
    if result is None:
        return None

    # 基本类型直接返回
    if isinstance(result, (str, int, float, bool)):
        return result

    # dict 直接返回
    if isinstance(result, dict):
        return result

    # 列表递归处理
    if isinstance(result, list):
        return [serialize_result(item) for item in result]

    # WxResponse 类型（有 __bool__ 方法，可以当 dict 用）
    # 尝试转换为 dict
    if hasattr(result, 'get') and hasattr(result, '__getitem__'):
        try:
            return dict(result)
        except (TypeError, ValueError):
            pass

    # 其他对象尝试提取公开属性
    try:
        attrs = {}
        for attr in dir(result):
            if attr.startswith('_'):
                continue
            try:
                value = getattr(result, attr)
                if not callable(value):
                    # 尝试 JSON 序列化测试
                    json.dumps(value, ensure_ascii=False)
                    attrs[attr] = value
            except (TypeError, ValueError, AttributeError):
                pass
        if attrs:
            return attrs
    except Exception:
        pass

    # 最后兜底：返回字符串表示
    return str(result)


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

    # 支持按行分批发送：每次最多 15 行(超过 130个字符也算一行)
    lines = content.splitlines()
    expanded_lines = []
    for ln in lines:
        if len(ln) <= 130:
            expanded_lines.append(ln)
        else:
            for i in range(0, len(ln), 130):
                expanded_lines.append(ln[i:i + 130])
    success = True

    # 之前需要分批，现在bug 修复了， 但是代码逻辑保留
    if True or len(expanded_lines) <= 18:
        success = robot.send_text_msg(content, receiver, at_receiver if at_receiver else None)
    else:
        for i in range(0, len(lines), 15):
            chunk = '\n'.join(lines[i:i + 15])
            mention = at_receiver if i == 0 and at_receiver else None
            ok = robot.send_text_msg(chunk, receiver, mention)
            if not ok:
                LOG.error(f"Failed to send text chunk starting at line {i} to [{receiver}]")
                success = False
                break

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


@app.route('/listen/add', methods=['POST'])
def add_listen():
    """
    添加聊天监听
    
    使用 Robot 的标准流程添加监听，会自动注入 on_message 回调。
    
    Request Body:
        - nickname: 聊天对象昵称
        
    Response:
        - data: {"success": bool}
    """
    robot = get_robot()
    if robot is None:
        return jsonify(ApiErrors.ROBOT_NOT_READY.to_dict())

    data = request.json or {}
    nickname = data.get('nickname', '')

    if not nickname:
        return jsonify(ApiErrors.INVALID_PARAMS.to_dict())

    try:
        success = robot.add_listen_chat(nickname)
        return jsonify(ApiResponse.success({"success": success}).to_dict())
    except Exception as e:
        LOG.error(f"AddListenChat failed for [{nickname}]: {e}")
        return jsonify(ApiResponse.error(107, f"AddListenChat failed: {str(e)}").to_dict())


@app.route('/execute/wx', methods=['POST'])
def execute_wx():
    """
    通用执行 WeChat 实例方法
    
    动态调用 WeChat 类的方法，支持大部分 wxautox4 提供的功能。
    
    Request Body:
        - name: 方法名 (如 "SendMsg", "ChatWith", "GetMyInfo")
        - params: 参数字典 (如 {"msg": "hello", "who": "xxx"})，可选
        
    Response:
        - data: 方法执行结果
        
    Note:
        - 不允许调用 __ 或 _ 开头的方法
        - 不允许调用黑名单中的危险方法 (ShutDown, KeepRunning 等)
        - AddListenChat 请使用 /listen/add 独立接口
    """
    robot = get_robot()
    if robot is None:
        return jsonify(ApiErrors.ROBOT_NOT_READY.to_dict())

    data = request.json or {}
    method_name = data.get('name', '')
    params = data.get('params', {})

    if not method_name:
        return jsonify(ApiResponse.error(103, "Missing 'name' parameter").to_dict())

    # 安全检查
    if not is_method_allowed(method_name):
        return jsonify(ApiResponse.error(106, f"Method '{method_name}' is not allowed").to_dict())

    # 获取 wx 实例
    try:
        wx = robot.client.wx
    except Exception as e:
        LOG.error(f"Failed to get wx instance: {e}")
        return jsonify(ApiResponse.error(101, "WeChat client not ready").to_dict())

    # 检查方法是否存在且可调用
    method = getattr(wx, method_name, None)
    if method is None or not callable(method):
        return jsonify(ApiResponse.error(106, f"Method '{method_name}' not found").to_dict())

    # 执行普通方法
    try:
        LOG.info(f"Executing wx.{method_name}({params})")
        result = method(**params) if params else method()
        serialized = serialize_result(result)
        LOG.info(f"wx.{method_name} result: {str(serialized)}")
        return jsonify(ApiResponse.success(serialized).to_dict())
    except TypeError as e:
        # 参数错误
        LOG.error(f"wx.{method_name} TypeError: {e}")
        return jsonify(ApiResponse.error(103, f"Invalid params: {str(e)}").to_dict())
    except Exception as e:
        LOG.error(f"wx.{method_name} execution failed: {e}")
        return jsonify(ApiResponse.error(107, f"Execution failed: {str(e)}").to_dict())


@app.route('/execute/chat', methods=['POST'])
def execute_chat():
    """
    通用执行 Chat 子窗口方法
    
    先通过 GetSubWindow 获取子窗口，再动态调用 Chat 类的方法。
    
    Request Body:
        - chat_name: 聊天对象名称 (用于 GetSubWindow 获取子窗口)
        - name: 方法名 (如 "SendMsg", "ChatInfo", "GetAllMessage")
        - params: 参数字典，可选
        
    Response:
        - data: 方法执行结果
        
    Note:
        - 子窗口必须已经存在（通过 AddListenChat 创建）
        - 不允许调用 __ 或 _ 开头的方法
    """
    robot = get_robot()
    if robot is None:
        return jsonify(ApiErrors.ROBOT_NOT_READY.to_dict())

    data = request.json or {}
    chat_name = data.get('chat_name', '')
    method_name = data.get('name', '')
    params = data.get('params', {})

    if not chat_name:
        return jsonify(ApiResponse.error(103, "Missing 'chat_name' parameter").to_dict())
    if not method_name:
        return jsonify(ApiResponse.error(103, "Missing 'name' parameter").to_dict())

    # 安全检查
    if not is_method_allowed(method_name):
        return jsonify(ApiResponse.error(106, f"Method '{method_name}' is not allowed").to_dict())

    # 获取 wx 实例
    try:
        wx = robot.client.wx
    except Exception as e:
        LOG.error(f"Failed to get wx instance: {e}")
        return jsonify(ApiResponse.error(101, "WeChat client not ready").to_dict())

    # 获取子窗口
    try:
        chat = wx.GetSubWindow(chat_name)
        if chat is None:
            return jsonify(
                ApiResponse.error(108, f"Sub window '{chat_name}' not found. Please add listener first.").to_dict())
    except Exception as e:
        LOG.error(f"GetSubWindow failed for [{chat_name}]: {e}")
        return jsonify(ApiResponse.error(108, f"Failed to get sub window: {str(e)}").to_dict())

    # 检查方法是否存在且可调用
    method = getattr(chat, method_name, None)
    if method is None or not callable(method):
        return jsonify(ApiResponse.error(106, f"Method '{method_name}' not found on Chat").to_dict())

    # 执行方法
    try:
        LOG.info(f"Executing chat[{chat_name}].{method_name}({params})")
        result = method(**params) if params else method()
        serialized = serialize_result(result)
        LOG.info(f"chat.{method_name} result: {str(serialized)}")
        return jsonify(ApiResponse.success(serialized).to_dict())
    except TypeError as e:
        # 参数错误
        LOG.error(f"chat.{method_name} TypeError: {e}")
        return jsonify(ApiResponse.error(103, f"Invalid params: {str(e)}").to_dict())
    except Exception as e:
        LOG.error(f"chat.{method_name} execution failed: {e}")
        return jsonify(ApiResponse.error(107, f"Execution failed: {str(e)}").to_dict())


@app.route('/execute/batch-chat-info', methods=['POST'])
def batch_chat_info():
    """
    批量获取 Chat 的 ChatInfo
    
    一次性获取多个聊天窗口的状态信息，避免多次请求。
    
    Request Body:
        - chat_names: 聊天对象名称列表
        
    Response:
        - data: {
            "results": {
                "chat_name1": {"success": true, "data": {...}},
                "chat_name2": {"success": false, "reason": "window_not_found"},
                ...
            }
        }
    """
    robot = get_robot()
    if robot is None:
        return jsonify(ApiErrors.ROBOT_NOT_READY.to_dict())

    data = request.json or {}
    chat_names = data.get('chat_names', [])

    if not chat_names or not isinstance(chat_names, list):
        return jsonify(ApiResponse.error(103, "Missing or invalid 'chat_names' parameter").to_dict())

    # 获取 wx 实例
    try:
        wx = robot.client.wx
    except Exception as e:
        LOG.error(f"Failed to get wx instance: {e}")
        return jsonify(ApiResponse.error(101, "WeChat client not ready").to_dict())

    results = {}

    for chat_name in chat_names:
        try:
            # 获取子窗口
            chat = wx.GetSubWindow(chat_name)
            if chat is None:
                results[chat_name] = {"success": False, "reason": "window_not_found"}
                continue

            # 调用 ChatInfo
            chat_info = chat.ChatInfo()
            serialized = serialize_result(chat_info)
            results[chat_name] = {"success": True, "data": serialized}

        except Exception as e:
            LOG.error(f"batch_chat_info failed for [{chat_name}]: {e}")
            results[chat_name] = {"success": False, "reason": str(e)}

    LOG.info(f"batch_chat_info completed for {len(chat_names)} chats")
    return jsonify(ApiResponse.success({"results": results}).to_dict())


# ==================== Middleware ====================

# 不记录日志的路径（健康检查等高频接口）
SKIP_LOG_PATHS = {"/health", "/ping"}


@app.before_request
def before_request_logging():
    """请求前日志"""
    g.start_time = time.time()
    # OPTIONS 请求和健康检查不记录日志
    if request.method == 'OPTIONS' or request.path in SKIP_LOG_PATHS:
        return
    body = request.get_data(as_text=True)
    LOG.info(f"Request: [{request.method} {request.path}], body: {body[:2000]}")


@app.after_request
def after_request_handler(response):
    """请求后处理：日志 + CORS"""
    # CORS headers
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'

    # 日志（OPTIONS 请求和健康检查不记录）
    if request.method != 'OPTIONS' and request.path not in SKIP_LOG_PATHS and hasattr(g, 'start_time'):
        cost = (time.time() - g.start_time) * 1000
        body = response.get_data(as_text=True)
        LOG.info(f"Response: [{request.method} {request.path}], cost: {cost:.0f}ms, body: {body[:2000]}")
    # 操作完成后，让 UI 稳定一下（仅对实际操作的接口）
    if request.path in ['/send/text']:
        time.sleep(random.uniform(0.02, 0.05))
    if request.path in ['/send/file']:
        time.sleep(random.uniform(0.1, 0.2))
    return response


# ==================== Server Control ====================

# Waitress 配置
WAITRESS_THREADS = 1  # 工作线程数
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
