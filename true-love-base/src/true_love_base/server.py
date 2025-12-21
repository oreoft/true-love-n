# -*- coding: utf-8 -*-
"""
HTTP Server - 提供 HTTP API 服务

提供外部调用接口，用于发送消息等操作。
使用 Waitress 作为生产级 WSGI 服务器。
"""

import json
import logging
import time
from threading import Thread
from typing import Optional, TYPE_CHECKING, Any

from flask import Flask, g, request, jsonify
from waitress import serve

from true_love_base.models.api import ApiResponse, ApiErrors
from true_love_base.utils.path_resolver import resolve_path
from true_love_base.services.log_service import LogType, get_log_service

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
}

# 需要特殊处理的方法（需要 callback 参数）
CALLBACK_METHODS = {'AddListenChat'}


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

    success = robot.send_text_msg(content, receiver, at_receiver if at_receiver else None)

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


@app.route('/listen/status', methods=['GET'])
def get_listener_status():
    """
    获取监听状态（以 DB 为基准，ChatInfo 响应为健康金标准）
    
    状态定义（只有两种）：
    - healthy: 子窗口存在 AND ChatInfo 能正确响应
    - unhealthy: 子窗口不存在 OR ChatInfo 无法响应
    
    Response:
        - data: 状态结果，包含:
            - listeners: 每个监听的状态列表
              - chat: 聊天名称
              - status: healthy / unhealthy
              - reason: 不健康的原因（可选）
            - summary: 状态汇总 {"healthy": N, "unhealthy": M}
    """
    robot = get_robot()
    if robot is None:
        return jsonify(ApiErrors.ROBOT_NOT_READY.to_dict())

    result = robot.get_listener_status()
    return jsonify(ApiResponse.success(result).to_dict())


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
    智能刷新监听列表（以 DB 为基准，结合健康检测）
    
    流程：
    1. 从 DB 获取配置的监听列表
    2. 执行健康检测（ChatInfo 响应检测）
    3. 分类处理：
       - healthy: 不处理（skip）
       - unhealthy: 执行 reset
    
    Response:
        - data: 刷新结果，包含:
            - total: 总监听数
            - success_count: 成功数
            - fail_count: 失败数
            - listeners: 每个监听的详情列表
              - chat: 聊天名称
              - before: 刷新前状态 (healthy/unhealthy)
              - action: 执行的操作 (skip/reset)
              - after: 刷新后状态
              - success: 是否成功
    """
    robot = get_robot()
    if robot is None:
        return jsonify(ApiErrors.ROBOT_NOT_READY.to_dict())

    result = robot.refresh_listen_chats()
    return jsonify(ApiResponse.success(result).to_dict())


@app.route('/listen/reset', methods=['POST'])
def reset_listener():
    """
    重置单个监听（基于 DB 配置）
    
    通过关闭子窗口、移除监听、重新添加监听的方式恢复异常的监听。
    只能重置 DB 中已配置的监听。
    
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
    重置所有监听（基于 DB 配置）
    
    通过停止所有监听、关闭所有子窗口、切换页面刷新 UI、重新添加所有监听的方式恢复。
    以 DB 中的配置为基准，不依赖内存状态。
    
    Response:
        - data: 重置结果，包含 success, message, total, recovered, failed, steps
    """
    robot = get_robot()
    if robot is None:
        return jsonify(ApiErrors.ROBOT_NOT_READY.to_dict())

    result = robot.reset_all_listeners()
    return jsonify(ApiResponse.success(result).to_dict())


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
        - AddListenChat 会自动注入 on_message 回调
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

    # 特殊处理需要 callback 的方法
    if method_name in CALLBACK_METHODS:
        if method_name == 'AddListenChat':
            nickname = params.get('nickname', '')
            if not nickname:
                return jsonify(ApiResponse.error(103, "Missing 'nickname' in params for AddListenChat").to_dict())
            try:
                # 使用 robot 的标准流程添加监听
                success = robot.add_listen_chat(nickname)
                return jsonify(ApiResponse.success({"success": success}).to_dict())
            except Exception as e:
                LOG.error(f"AddListenChat failed for [{nickname}]: {e}")
                return jsonify(ApiResponse.error(107, f"AddListenChat failed: {str(e)}").to_dict())

    # 执行普通方法
    try:
        LOG.info(f"Executing wx.{method_name}({params})")
        result = method(**params) if params else method()
        serialized = serialize_result(result)
        LOG.info(f"wx.{method_name} result: {str(serialized)[:200]}")
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
        LOG.info(f"chat.{method_name} result: {str(serialized)[:200]}")
        return jsonify(ApiResponse.success(serialized).to_dict())
    except TypeError as e:
        # 参数错误
        LOG.error(f"chat.{method_name} TypeError: {e}")
        return jsonify(ApiResponse.error(103, f"Invalid params: {str(e)}").to_dict())
    except Exception as e:
        LOG.error(f"chat.{method_name} execution failed: {e}")
        return jsonify(ApiResponse.error(107, f"Execution failed: {str(e)}").to_dict())


@app.route('/logs', methods=['GET'])
def handle_logs():
    """
    日志操作接口
    
    支持两种操作：
    - query: 查询日志，支持增量查询
    - truncate: 清空指定日志文件
    
    Query Params:
        - action: 操作类型，query 或 truncate（默认 query）
        - log_type: 日志类型，info 或 error（默认 info）
        - limit: 返回的最大行数，默认 100，最大 500（仅 query 有效）
        - since_offset: 上次查询返回的 next_offset（仅 query 有效）
    """
    action = request.args.get('action', 'query').lower()
    log_type_str = request.args.get('log_type', 'info').lower()

    # 校验日志类型
    try:
        log_type = LogType(log_type_str)
    except ValueError:
        return jsonify(ApiResponse.error(100, f"不支持的日志类型: {log_type_str}").to_dict())

    log_service = get_log_service()

    if action == 'query':
        # 查询日志
        limit = request.args.get('limit', 100, type=int)
        since_offset = request.args.get('since_offset', 0, type=int)

        result = log_service.query_logs(
            log_type=log_type,
            since_offset=since_offset if since_offset > 0 else None,
            limit=limit
        )

        return jsonify(ApiResponse.success({
            "lines": result.lines,
            "next_offset": result.next_offset,
            "total_lines": result.total_lines,
            "has_more": result.has_more
        }).to_dict())

    elif action == 'truncate':
        # 清空日志
        success = log_service.truncate_log(log_type)
        if not success:
            return jsonify(ApiResponse.error(101, f"清空 {log_type_str} 日志失败").to_dict())
        return jsonify(ApiResponse.success({
            "message": f"{log_type_str} 日志已清空",
            "log_type": log_type_str
        }).to_dict())

    else:
        return jsonify(ApiResponse.error(100, f"不支持的操作类型: {action}").to_dict())


# ==================== Middleware ====================

@app.before_request
def before_request_logging():
    """请求前日志"""
    g.start_time = time.time()
    # OPTIONS 请求不记录日志
    if request.method == 'OPTIONS':
        return
    body = request.get_data(as_text=True)
    LOG.info(f"Request: [{request.method} {request.path}], body: {body[:200]}")


@app.after_request
def after_request_handler(response):
    """请求后处理：日志 + CORS"""
    # CORS headers
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'

    # 日志（OPTIONS 请求不记录）
    if request.method != 'OPTIONS' and hasattr(g, 'start_time'):
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
