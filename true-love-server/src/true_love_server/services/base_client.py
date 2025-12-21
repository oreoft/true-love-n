# -*- coding: utf-8 -*-
"""
Base Client - 基础通信客户端

与 base 服务通信，发送消息、图片等。
"""

import json
import logging
import time

import requests

from ..core import Config

config = Config()
host = config.BASE_SERVER["host"]
text_url = f"{host}/send/text"
text_file = f"{host}/send/file"
get_by_room_id_url = f"{host}/get/by/room-id"
add_listen_url = f"{host}/listen/add"
execute_wx_url = f"{host}/execute/wx"
execute_chat_url = f"{host}/execute/chat"
LOG = logging.getLogger("BaseClient")


def send_text(send_receiver, at_receiver, content, raise_on_error: bool = False) -> tuple[bool, str]:
    """
    发送文本消息

    Args:
        send_receiver: 接收者
        at_receiver: @的用户
        content: 消息内容
        raise_on_error: 是否在失败时抛出异常

    Returns:
        (是否成功, 错误信息)
    """
    payload = json.dumps({
        "sendReceiver": send_receiver,
        "atReceiver": at_receiver,
        "content": content
    }, ensure_ascii=False)
    headers = {
        'Content-Type': 'application/json'
    }
    try:
        start_time = time.time()
        LOG.info("开始请求base推送text内容, req:[%s]", payload)
        res = requests.request("POST", text_url, headers=headers, data=payload, timeout=(2, 60))
        res.raise_for_status()
        LOG.info("请求成功, cost:[%.0fms], res:[%s]", (time.time() - start_time) * 1000, res.json())
        return True, ""
    except Exception as e:
        LOG.error("send_text 失败: %s", e)
        if raise_on_error:
            raise
        return False, str(e)


def send_img(path, send_receiver, raise_on_error: bool = False) -> tuple[bool, str]:
    """
    发送图片消息

    Args:
        path: 图片路径
        send_receiver: 接收者
        raise_on_error: 是否在失败时抛出异常

    Returns:
        (是否成功, 错误信息)
    """
    payload = json.dumps({
        "path": path,
        "sendReceiver": send_receiver,
    }, ensure_ascii=False)
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        start_time = time.time()
        LOG.info("开始请求base推送img内容, req:[%s]", payload[:2000])
        res = requests.request("POST", text_file, headers=headers, data=payload, timeout=(2, 60))
        res.raise_for_status()
        LOG.info("send_img请求成功, cost:[%.0fms], res:[%s]", (time.time() - start_time) * 1000, res.json())
        return True, ""
    except Exception as e:
        LOG.error("send_img 失败: %s", e)
        if raise_on_error:
            raise
        return False, str(e)


def send_video(path, send_receiver, raise_on_error: bool = False) -> tuple[bool, str]:
    """
    发送视频消息

    Args:
        path: 视频路径
        send_receiver: 接收者
        raise_on_error: 是否在失败时抛出异常

    Returns:
        (是否成功, 错误信息)
    """
    payload = json.dumps({
        "path": path,
        "sendReceiver": send_receiver,
    }, ensure_ascii=False)
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        start_time = time.time()
        LOG.info("开始请求base推送video内容, req:[%s]", payload[:2000])
        res = requests.request("POST", text_file, headers=headers, data=payload, timeout=(2, 60))
        res.raise_for_status()
        LOG.info("send_video请求成功, cost:[%.0fms], res:[%s]", (time.time() - start_time) * 1000, res.json())
        return True, ""
    except Exception as e:
        LOG.error("send_video 失败: %s", e)
        if raise_on_error:
            raise
        return False, str(e)


def get_by_room_id(room_id) -> dict:
    payload = json.dumps({
        "room_id": room_id,
    }, ensure_ascii=False)
    headers = {
        'Content-Type': 'application/json'
    }
    try:
        start_time = time.time()
        LOG.info("开始请求get_all内容")
        res = requests.request("POST", get_by_room_id_url, headers=headers, data=payload, timeout=(2, 60))
        res.raise_for_status()
        LOG.info("get_all请求成功, cost:[%.0fms], res:[%s]", (time.time() - start_time) * 1000, res.json())
        return res.json()['data']
    except Exception as e:
        LOG.error("get_all 失败: %s", e)
    return {}


# ==================== 监听管理接口 ====================

def add_listen_chat(nickname: str) -> dict:
    """
    添加聊天监听
    
    调用 Base 的 /listen/add 接口，会自动注入 on_message 回调。
    
    Args:
        nickname: 聊天对象昵称
    
    Returns:
        {"success": bool, "data": any, "message": str}
    """
    payload = json.dumps({
        "nickname": nickname
    }, ensure_ascii=False)
    headers = {'Content-Type': 'application/json'}
    
    try:
        start_time = time.time()
        LOG.info(f"add_listen_chat: [{nickname}]")
        res = requests.post(add_listen_url, headers=headers, data=payload, timeout=(2, 60))
        res.raise_for_status()
        result = res.json()
        LOG.info(f"add_listen_chat 成功, cost:[{(time.time() - start_time) * 1000:.0f}ms], code:[{result.get('code')}]")
        return {
            "success": result.get("code") == 0,
            "data": result.get("data"),
            "message": result.get("msg", "")
        }
    except Exception as e:
        LOG.exception(f"add_listen_chat 失败: {e}")
        return {"success": False, "data": None, "message": str(e)}


# ==================== 通用执行接口 ====================

def execute_wx(method_name: str, params: dict = None) -> dict:
    """
    调用 Base 的 /execute/wx 接口
    
    动态调用 WeChat 实例的方法。
    
    Args:
        method_name: 方法名（如 "GetAllSubWindow", "RemoveListenChat"）
        params: 参数字典（可选）
    
    Returns:
        {"success": bool, "data": any, "message": str}
        
    Note:
        AddListenChat 请使用 add_listen_chat() 函数
    """
    payload = json.dumps({
        "name": method_name,
        "params": params or {}
    }, ensure_ascii=False)
    headers = {'Content-Type': 'application/json'}
    
    try:
        start_time = time.time()
        LOG.info(f"execute_wx: {method_name}({params})")
        res = requests.post(execute_wx_url, headers=headers, data=payload, timeout=(2, 60))
        res.raise_for_status()
        result = res.json()
        LOG.info(f"execute_wx 成功, cost:[{(time.time() - start_time) * 1000:.0f}ms], code:[{result.get('code')}]")
        return {
            "success": result.get("code") == 0,
            "data": result.get("data"),
            "message": result.get("msg", "")
        }
    except Exception as e:
        LOG.exception(f"execute_wx 失败: {e}")
        return {"success": False, "data": None, "message": str(e)}


def execute_chat(chat_name: str, method_name: str, params: dict = None) -> dict:
    """
    调用 Base 的 /execute/chat 接口
    
    动态调用 Chat 子窗口的方法。
    
    Args:
        chat_name: 聊天对象名称（用于获取子窗口）
        method_name: 方法名（如 "ChatInfo", "Close", "SendMsg"）
        params: 参数字典（可选）
    
    Returns:
        {"success": bool, "data": any, "message": str}
    """
    payload = json.dumps({
        "chat_name": chat_name,
        "name": method_name,
        "params": params or {}
    }, ensure_ascii=False)
    headers = {'Content-Type': 'application/json'}
    
    try:
        start_time = time.time()
        LOG.info(f"execute_chat[{chat_name}]: {method_name}({params})")
        res = requests.post(execute_chat_url, headers=headers, data=payload, timeout=(2, 60))
        res.raise_for_status()
        result = res.json()
        LOG.info(f"execute_chat 成功, cost:[{(time.time() - start_time) * 1000:.0f}ms], code:[{result.get('code')}]")
        return {
            "success": result.get("code") == 0,
            "data": result.get("data"),
            "message": result.get("msg", "")
        }
    except Exception as e:
        LOG.exception(f"execute_chat 失败: {e}")
        return {"success": False, "data": None, "message": str(e)}
