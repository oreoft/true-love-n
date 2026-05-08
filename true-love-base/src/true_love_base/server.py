# -*- coding: utf-8 -*-
"""
HTTP Server - 提供 HTTP API 服务

提供外部调用接口，用于发送消息等操作。
使用 FastAPI + Uvicorn 提供 HTTP 服务。
"""

import json
import logging
from threading import Thread
from typing import TYPE_CHECKING, Any, Optional

import uvicorn
from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from true_love_base.models.api import ApiErrors, ApiResponse
from true_love_base.utils.path_resolver import resolve_path

if TYPE_CHECKING:
    from true_love_base.services.robot import Robot

app = FastAPI(title="True Love Base", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LOG = logging.getLogger("Server")

# 全局 Robot 实例
_robot: Optional["Robot"] = None


def get_robot() -> Optional["Robot"]:
    """获取 Robot 实例"""
    return _robot


# ==================== 通用执行接口配置 ====================

# 方法黑名单 - 禁止调用的方法
METHOD_BLACKLIST = {
    "ShutDown",  # 危险：会杀掉微信进程
    "KeepRunning",  # 阻塞方法，不应通过 API 调用
    "StartListening",  # 阻塞方法
    "StopListening",  # 可能影响正常监听
    "AddListenChat",  # 需要 callback，使用 /listen/add 独立接口
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
    if method_name.startswith("__"):
        return False
    # 过滤 _ 开头的私有方法
    if method_name.startswith("_"):
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
    if hasattr(result, "get") and hasattr(result, "__getitem__"):
        try:
            return dict(result)
        except (TypeError, ValueError):
            pass

    # 其他对象尝试提取公开属性
    try:
        attrs = {}
        for attr in dir(result):
            if attr.startswith("_"):
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


def _payload(data: dict[str, Any] | None) -> dict[str, Any]:
    return data or {}


# ==================== API Routes ====================


@app.get("/", response_class=PlainTextResponse)
async def root() -> str:
    """健康检查"""
    return "pong"


@app.get("/ping", response_class=PlainTextResponse)
async def ping() -> str:
    """健康检查"""
    return "pong"


MAX_CHUNK_BYTES = 2000


def split_long_text(text: str) -> list[str]:
    """
    将文本按 UTF-8 字节长度进行拆分，每批不超过 MAX_CHUNK_BYTES。
    尽量在换行符处拆分以保持美观。
    """
    chunks = []
    if not text:
        return chunks

    remaining = text
    while remaining:
        # 如果剩余部分转为字节后小于限制，直接添加并结束
        if len(remaining.encode("utf-8")) <= MAX_CHUNK_BYTES:
            chunks.append(remaining)
            break

        # 寻找当前能容纳的最大字符数量
        low = 0
        high = len(remaining)
        split_point = 0
        while low <= high:
            mid = (low + high) // 2
            if len(remaining[:mid].encode("utf-8")) <= MAX_CHUNK_BYTES:
                split_point = mid
                low = mid + 1
            else:
                high = mid - 1

        # 在这 2000 字节的范围内，尝试找最后一个换行符进行美化分割
        chunk_text = remaining[:split_point]
        last_newline = chunk_text.rfind("\n")
        # 如果找到了换行符，且它占据了当前块一半以上的长度，则从这儿切
        if last_newline != -1 and last_newline > split_point * 0.6:
            actual_split = last_newline + 1
        else:
            actual_split = split_point

        chunks.append(remaining[:actual_split])
        remaining = remaining[actual_split:]

    return chunks


@app.post("/send/text")
async def send_text(request: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    """
    发送文本消息

    Request Body:
        - sendReceiver: 接收者
        - content: 消息内容
        - atReceiver: 要@的人（可选）

    超过 2000 个字符时自动分批：在每批末尾 200 字符内寻找换行符切割，
    分批依次发送，仅第一批携带 @。
    """
    robot = get_robot()
    if robot is None:
        return ApiErrors.ROBOT_NOT_READY.to_dict()

    data = _payload(request)
    receiver = data.get("sendReceiver", "")
    content = data.get("content", "")
    at_receiver = data.get("atReceiver", "")

    if not receiver or not content:
        return ApiErrors.INVALID_PARAMS.to_dict()

    if len(content.encode("utf-8")) <= MAX_CHUNK_BYTES:
        # 短消息直接发送
        success = robot.send_text_msg(content, receiver, at_receiver if at_receiver else None)
    else:
        # 长消息分段发送
        chunks = split_long_text(content)
        LOG.info(
            "send_text: content too long (%d bytes), splitting into %d chunks",
            len(content.encode("utf-8")),
            len(chunks),
        )
        success = True
        for idx, chunk in enumerate(chunks):
            mention = at_receiver if idx == 0 and at_receiver else None
            ok = robot.send_text_msg(chunk, receiver, mention)
            if not ok:
                LOG.error("send_text: failed on chunk %d/%d to [%s]", idx + 1, len(chunks), receiver)
                success = False
                break

    if success:
        return ApiResponse.success().to_dict()
    return ApiErrors.SEND_FAILED.to_dict()


@app.post("/send/file")
async def send_file(request: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    """
    发送文件

    Request Body:
        - sendReceiver: 接收者
        - path: 文件路径（可以是 Server 的相对路径，会自动在 true-love-server 目录下查找）
    """
    robot = get_robot()
    if robot is None:
        return ApiErrors.ROBOT_NOT_READY.to_dict()

    data = _payload(request)
    path = data.get("path", "")
    receiver = data.get("sendReceiver", "")

    if not receiver or not path:
        return ApiErrors.INVALID_PARAMS.to_dict()

    # 解析 Server 相对路径
    try:
        resolved_path = resolve_path(path)
    except FileNotFoundError as e:
        LOG.error("Failed to send file to [%s]: %s", receiver, e)
        return ApiErrors.SEND_FAILED.to_dict()

    success = robot.send_file_msg(resolved_path, receiver)

    if success:
        return ApiResponse.success().to_dict()
    return ApiErrors.SEND_FAILED.to_dict()


@app.post("/listen/add")
async def add_listen(request: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
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
        return ApiErrors.ROBOT_NOT_READY.to_dict()

    data = _payload(request)
    nickname = data.get("nickname", "")

    if not nickname:
        return ApiErrors.INVALID_PARAMS.to_dict()

    try:
        success = robot.add_listen_chat(nickname)
        return ApiResponse.success({"success": success}).to_dict()
    except Exception as e:
        LOG.error("AddListenChat failed for [%s]: %s", nickname, e)
        return ApiResponse.error(107, f"AddListenChat failed: {str(e)}").to_dict()


@app.post("/execute/wx")
async def execute_wx(request: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
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
        return ApiErrors.ROBOT_NOT_READY.to_dict()

    data = _payload(request)
    method_name = data.get("name", "")
    params = data.get("params", {})

    if not method_name:
        return ApiResponse.error(103, "Missing 'name' parameter").to_dict()

    # 安全检查
    if not is_method_allowed(method_name):
        return ApiResponse.error(106, f"Method '{method_name}' is not allowed").to_dict()

    # 获取 wx 实例
    try:
        wx = robot.client.wx
    except Exception as e:
        LOG.error("Failed to get wx instance: %s", e)
        return ApiResponse.error(101, "WeChat client not ready").to_dict()

    # 检查方法是否存在且可调用
    method = getattr(wx, method_name, None)
    if method is None or not callable(method):
        return ApiResponse.error(106, f"Method '{method_name}' not found").to_dict()

    # 执行普通方法
    try:
        LOG.info("Executing wx.%s(%s)", method_name, params)
        result = method(**params) if params else method()
        serialized = serialize_result(result)
        LOG.info("wx.%s result: %s", method_name, str(serialized))
        return ApiResponse.success(serialized).to_dict()
    except TypeError as e:
        # 参数错误
        LOG.error("wx.%s TypeError: %s", method_name, e)
        return ApiResponse.error(103, f"Invalid params: {str(e)}").to_dict()
    except Exception as e:
        LOG.error("wx.%s execution failed: %s", method_name, e)
        return ApiResponse.error(107, f"Execution failed: {str(e)}").to_dict()


@app.post("/execute/chat")
async def execute_chat(request: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
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
        return ApiErrors.ROBOT_NOT_READY.to_dict()

    data = _payload(request)
    chat_name = data.get("chat_name", "")
    method_name = data.get("name", "")
    params = data.get("params", {})

    if not chat_name:
        return ApiResponse.error(103, "Missing 'chat_name' parameter").to_dict()
    if not method_name:
        return ApiResponse.error(103, "Missing 'name' parameter").to_dict()

    # 安全检查
    if not is_method_allowed(method_name):
        return ApiResponse.error(106, f"Method '{method_name}' is not allowed").to_dict()

    # 获取 wx 实例
    try:
        wx = robot.client.wx
    except Exception as e:
        LOG.error("Failed to get wx instance: %s", e)
        return ApiResponse.error(101, "WeChat client not ready").to_dict()

    # 获取子窗口
    try:
        chat = wx.GetSubWindow(chat_name)
        if chat is None:
            return ApiResponse.error(108, f"Sub window '{chat_name}' not found. Please add listener first.").to_dict()
    except Exception as e:
        LOG.error("GetSubWindow failed for [%s]: %s", chat_name, e)
        return ApiResponse.error(108, f"Failed to get sub window: {str(e)}").to_dict()

    # 检查方法是否存在且可调用
    method = getattr(chat, method_name, None)
    if method is None or not callable(method):
        return ApiResponse.error(106, f"Method '{method_name}' not found on Chat").to_dict()

    # 执行方法
    try:
        LOG.info("Executing chat[%s].%s(%s)", chat_name, method_name, params)
        result = method(**params) if params else method()
        serialized = serialize_result(result)
        LOG.info("chat.%s result: %s", method_name, str(serialized))
        return ApiResponse.success(serialized).to_dict()
    except TypeError as e:
        # 参数错误
        LOG.error("chat.%s TypeError: %s", method_name, e)
        return ApiResponse.error(103, f"Invalid params: {str(e)}").to_dict()
    except Exception as e:
        LOG.error("chat.%s execution failed: %s", method_name, e)
        return ApiResponse.error(107, f"Execution failed: {str(e)}").to_dict()


@app.post("/execute/batch-chat-info")
async def batch_chat_info(request: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
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
        return ApiErrors.ROBOT_NOT_READY.to_dict()

    data = _payload(request)
    chat_names = data.get("chat_names", [])

    if not chat_names or not isinstance(chat_names, list):
        return ApiResponse.error(103, "Missing or invalid 'chat_names' parameter").to_dict()

    # 获取 wx 实例
    try:
        wx = robot.client.wx
    except Exception as e:
        LOG.error("Failed to get wx instance: %s", e)
        return ApiResponse.error(101, "WeChat client not ready").to_dict()

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
            LOG.error("batch_chat_info failed for [%s]: %s", chat_name, e)
            results[chat_name] = {"success": False, "reason": str(e)}

    LOG.info("batch_chat_info completed for %d chats", len(chat_names))
    return ApiResponse.success({"results": results}).to_dict()


# ==================== Server Control ====================


def enable_http(robot: "Robot", host: str = "0.0.0.0", port: int = 5000) -> None:
    """
    启动 HTTP 服务（使用 Uvicorn）

    Args:
        robot: Robot 实例
        host: 绑定地址
        port: 端口
    """
    global _robot
    _robot = robot

    def run_server() -> None:
        """运行 Uvicorn 服务器"""
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="warning",
            access_log=False,
        )

    t = Thread(
        target=run_server,
        name="HttpServer",
        daemon=True,  # 守护线程，主线程退出时自动结束
    )
    t.start()

    LOG.info("HTTP server (Uvicorn) started on %s:%s", host, port)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")
