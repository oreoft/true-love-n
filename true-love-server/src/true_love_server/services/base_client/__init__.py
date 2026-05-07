# -*- coding: utf-8 -*-
"""
Base Client — 多平台消息发送客户端

使用方式：
    from ..services import base_client

    # 方式一：通过工厂获取实例（推荐新代码使用）
    client = base_client.get_base_client(platform)
    client.send_text(receiver, at_user, content)

    # 方式二：模块级快捷函数
    base_client.send_text(receiver, at_user, content, platform=platform)

新增平台：
    1. 在本包内新建 _newplatform.py，实现 BaseClient
    2. 在下方 _REGISTRY 注册一行
"""

from ._interface import BaseClient
from ._wechat import WeChatBaseClient
from ._lark import LarkBaseClient

__all__ = ["BaseClient", "WeChatBaseClient", "LarkBaseClient", "get_base_client"]

from ... import Config

# ==================== 平台注册表（新增平台只需在此加一行）====================

_REGISTRY: dict[str, type[BaseClient]] = {
    "wechat": WeChatBaseClient,
    "lark": LarkBaseClient,
}


def get_base_client(platform: str = "wechat") -> BaseClient:
    """根据平台名称返回对应的 BaseClient 实例。"""
    cfg = Config()
    base_server: dict = cfg.BASE_SERVER or {}
    host = base_server.get("hosts", {}).get(platform, "")

    token_list = cfg.HTTP_TOKEN or []
    token = token_list[0] if token_list else ""

    client_cls = _REGISTRY.get(platform, WeChatBaseClient)
    return client_cls(host=host, token=token)


# ==================== 模块级快捷函数 ====================

def send_text(send_receiver: str, at_receiver: str, content: str,
              platform: str = "wechat", raise_on_error: bool = False) -> tuple[bool, str]:
    return get_base_client(platform).send_text(send_receiver, at_receiver, content,
                                               raise_on_error=raise_on_error)


def send_file(ref: str, receiver: str,
              platform: str = "wechat", raise_on_error: bool = False) -> tuple[bool, str]:
    return get_base_client(platform).send_file(ref, receiver, raise_on_error=raise_on_error)


def send_img(path: str, send_receiver: str, raise_on_error: bool = False) -> tuple[bool, str]:
    return get_base_client("wechat").send_img(path, send_receiver, raise_on_error=raise_on_error)


def send_video(path: str, send_receiver: str, raise_on_error: bool = False) -> tuple[bool, str]:
    return get_base_client("wechat").send_video(path, send_receiver, raise_on_error=raise_on_error)


def execute_wx(method_name: str, params: dict = None) -> dict:
    return get_base_client("wechat").execute_wx(method_name, params)


def execute_chat(chat_name: str, method_name: str, params: dict = None) -> dict:
    return get_base_client("wechat").execute_chat(chat_name, method_name, params)


def add_listen_chat(nickname: str) -> dict:
    return get_base_client("wechat").add_listen_chat(nickname)


def batch_chat_info(chat_names: list[str]) -> dict:
    return get_base_client("wechat").batch_chat_info(chat_names)


def get_by_room_id(room_id) -> dict:
    return get_base_client("wechat").get_by_room_id(room_id)
