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
get_by_room_id_url = f"{host}/get/by/room-id"
listen_list_url = f"{host}/listen/list"
listen_add_url = f"{host}/listen/add"
listen_remove_url = f"{host}/listen/remove"
LOG = logging.getLogger("BaseClient")


def send_text(send_receiver, at_receiver, content):
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
        # 检查HTTP响应状态
        res.raise_for_status()
        LOG.info("请求成功, cost:[%.0fms], res:[%s]", (time.time() - start_time) * 1000, res.json())
    except Exception as e:
        LOG.info("send_text 失败", e)
    return ""


def send_img(path, send_receiver):
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
        # 检查HTTP响应状态
        res.raise_for_status()
        LOG.info("send_img请求成功, cost:[%.0fms], res:[%s]", (time.time() - start_time) * 1000, res.json())
    except Exception as e:
        LOG.info("send_img 失败", e)
    return ""


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
        # 检查HTTP响应状态
        res.raise_for_status()
        LOG.info("get_all请求成功, cost:[%.0fms], res:[%s]", (time.time() - start_time) * 1000, res.json())
        return res.json()['data']
    except Exception as e:
        LOG.info("get_all 失败", e)
    return {}


def get_listen_list() -> list | None:
    """
    获取所有监听对象列表
    
    Returns:
        监听对象列表，失败返回 None
    """
    try:
        start_time = time.time()
        LOG.info("开始请求监听列表")
        res = requests.get(listen_list_url, timeout=(2, 60))
        res.raise_for_status()
        LOG.info("get_listen_list请求成功, cost:[%.0fms], res:[%s]", (time.time() - start_time) * 1000, res.json())
        return res.json().get('data', [])
    except Exception as e:
        LOG.exception("get_listen_list 失败: %s", e)
    return None


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
