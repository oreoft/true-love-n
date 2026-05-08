# -*- coding: utf-8 -*-
"""
Base Client — 多平台消息发送客户端

使用方式：
    from ..services import base_client

    # 跨平台操作（send_text / send_file）：直接用模块级快捷函数
    base_client.send_text(receiver, at_user, content, platform=platform)

    # 微信专属操作（execute_wx / send_img 等）：获取 wechat 实例后调用
    wechat = base_client.get_wechat_client()
    wechat.execute_wx("GetAllSubWindow", {})
    wechat.send_img(path, receiver)

新增平台：
    1. 在本包内新建 _newplatform.py，实现 BaseClient
    2. 在下方 _REGISTRY 注册一行
"""

from ._interface import BaseClient
from ._wechat import WeChatBaseClient
from ._lark import LarkBaseClient

__all__ = ["BaseClient", "WeChatBaseClient", "LarkBaseClient", "get_base_client", "get_wechat_client"]

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
    if platform not in _REGISTRY:
        raise ValueError(f"未注册的平台: {platform}")

    hosts = base_server.get("hosts", {}) or {}
    host = hosts.get(platform) or (base_server.get("host", "") if platform == "wechat" else "")
    if not host:
        raise ValueError(f"base_server.hosts.{platform} 未配置")

    token_list = cfg.HTTP_TOKEN or []
    token = token_list[0] if token_list else ""

    client_cls = _REGISTRY[platform]
    return client_cls(host=host, token=token)


def get_wechat_client() -> WeChatBaseClient:
    """返回微信平台的 BaseClient 实例，供调用方直接调用微信专属方法。"""
    return get_base_client("wechat")


# ==================== 跨平台模块级快捷函数 ====================

async def send_text(send_receiver: str, at_receiver: str, content: str,
                    platform: str = "wechat", raise_on_error: bool = False) -> tuple[bool, str]:
    try:
        return await get_base_client(platform).send_text(send_receiver, at_receiver, content,
                                                         raise_on_error=raise_on_error)
    except Exception as e:
        if raise_on_error:
            raise
        return False, str(e)


async def send_file(ref: str, receiver: str,
                    platform: str = "wechat", raise_on_error: bool = False) -> tuple[bool, str]:
    try:
        return await get_base_client(platform).send_file(ref, receiver, raise_on_error=raise_on_error)
    except Exception as e:
        if raise_on_error:
            raise
        return False, str(e)
