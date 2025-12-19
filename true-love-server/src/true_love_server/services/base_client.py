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
text_img = f"{host}/send/img"
text_video = f"{host}/send/video"
get_by_room_id_url = f"{host}/get/by/room-id"
listen_status_url = f"{host}/listen/status"
listen_add_url = f"{host}/listen/add"
listen_remove_url = f"{host}/listen/remove"
listen_refresh_url = f"{host}/listen/refresh"
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
        LOG.info("开始请求base推送img内容, req:[%s]", payload[:200])
        res = requests.request("POST", text_img, headers=headers, data=payload, timeout=(2, 60))
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
        LOG.info("开始请求base推送video内容, req:[%s]", payload[:200])
        res = requests.request("POST", text_video, headers=headers, data=payload, timeout=(2, 60))
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


def get_listen_status() -> dict | None:
    """
    获取监听状态

    Args:
        probe: 是否执行主动探测（ChatInfo 检测）

    Returns:
        监听状态字典，包含:
        - listeners: 每个监听的状态列表
        - summary: 状态汇总
        - probe_mode: 是否为探测模式
        失败返回 None
    """
    try:
        start_time = time.time()
        LOG.info("开始get_listen_status监听状态")
        res = requests.get(listen_status_url, params={}, timeout=(2, 60))
        res.raise_for_status()
        LOG.info("get_listen_status请求成功, cost:[%.0fms], res:[%s]", (time.time() - start_time) * 1000, res.json())
        return res.json().get('data')
    except Exception as e:
        LOG.exception("get_listen_status 失败: %s", e)
    return None


def get_listen_list() -> list | None:
    """
    获取所有监听对象列表（从状态接口提取）

    Returns:
        监听对象列表，失败返回 None
    """
    status = get_listen_status()
    # 检查 status 是否有效（可能是 None、空字符串、或其他非字典类型）
    if not status or not isinstance(status, dict):
        return None
    listeners = status.get('listeners', [])
    return [item.get('chat') for item in listeners if item.get('chat')]


def add_listen(chat_name: str) -> tuple[bool, str]:
    """
    添加监听对象

    Args:
        chat_name: 要监听的聊天名称

    Returns:
        (是否成功, 消息)
    """
    payload = json.dumps({
        "chat_name": chat_name,
    }, ensure_ascii=False)
    headers = {
        'Content-Type': 'application/json'
    }
    try:
        start_time = time.time()
        LOG.info("开始添加监听: %s", chat_name)
        res = requests.post(listen_add_url, headers=headers, data=payload, timeout=(2, 60))
        res.raise_for_status()
        result = res.json()
        LOG.info("add_listen请求成功, cost:[%.0fms], res:[%s]", (time.time() - start_time) * 1000, result)
        return True, result.get('msg', '成功')
    except Exception as e:
        LOG.exception("add_listen 失败: %s", e)
    return False, str(e)


def remove_listen(chat_name: str) -> tuple[bool, str]:
    """
    删除监听对象

    Args:
        chat_name: 要删除的聊天名称

    Returns:
        (是否成功, 消息)
    """
    payload = json.dumps({
        "chat_name": chat_name,
    }, ensure_ascii=False)
    headers = {
        'Content-Type': 'application/json'
    }
    try:
        start_time = time.time()
        LOG.info("开始删除监听: %s", chat_name)
        res = requests.post(listen_remove_url, headers=headers, data=payload, timeout=(2, 60))
        res.raise_for_status()
        result = res.json()
        LOG.info("remove_listen请求成功, cost:[%.0fms], res:[%s]", (time.time() - start_time) * 1000, result)
        return True, result.get('msg', '成功')
    except Exception as e:
        LOG.exception("remove_listen 失败: %s", e)
    return False, str(e)


def refresh_listen() -> tuple[bool, dict | None, str]:
    """
    刷新监听列表（智能刷新，以 DB 为基准）

    Returns:
        (是否成功, 刷新结果数据, 消息)
        刷新结果数据包含:
        - total: 总监听数
        - success_count: 成功数
        - fail_count: 失败数
        - listeners: 每个监听的详情列表
    """
    try:
        start_time = time.time()
        LOG.info("开始刷新监听列表")
        res = requests.post(listen_refresh_url, timeout=(2, 120))
        res.raise_for_status()
        result = res.json()
        LOG.info("refresh_listen请求成功, cost:[%.0fms], res:[%s]", (time.time() - start_time) * 1000, result)
        return True, result.get('data'), result.get('message', '成功')
    except Exception as e:
        LOG.exception("refresh_listen 失败: %s", e)
    return False, None, str(e)
