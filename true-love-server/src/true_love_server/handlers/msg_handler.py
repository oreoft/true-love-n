# -*- coding: utf-8 -*-
"""
Message Handler - 消息处理器

统一消息入口，使用注册表分发到具体处理器。
"""

import logging
from concurrent.futures import ThreadPoolExecutor

from ..core import local_msg_id
from ..models.chat_msg import ChatMsg
from ..services import base_client

# 导入所有处理器以触发注册（顺序无关，按优先级排序）
from . import query_handler      # noqa: F401
from . import task_handler       # noqa: F401
from . import reminder_handler   # noqa: F401
from . import admin_handler      # noqa: F401
from . import image_gen_handler  # noqa: F401
from . import chat_handler       # noqa: F401

from .registry import registry

LOG = logging.getLogger("MsgHandler")

# 线程池
_executor = ThreadPoolExecutor(max_workers=10)


class MsgHandler:
    """
    消息处理器

    统一的消息入口，使用注册表分发到具体处理器。
    """

    def __init__(self):
        self.LOG = logging.getLogger("MsgHandler")

    def handler_msg(self, msg: ChatMsg) -> str:
        """
        处理消息（同步版本）

        Args:
            msg: 聊天消息

        Returns:
            回复内容
        """
        # 清理消息内容
        cleaned_content = msg.content.replace("@真爱粉", "").replace("zaf", "").strip()

        # 设置上下文（用于追踪）
        local_msg_id.set(f"{msg.sender}_{msg.chat_id}")

        # 从注册表获取处理器
        handler = registry.get_handler(msg, cleaned_content)

        if handler:
            self.LOG.info("消息由 [%s] 处理, sender=%s", handler.name, msg.sender)
            result = handler.handle(msg, cleaned_content)
            return result if result else ""

        # 不应该到达这里（ChatHandler 作为兜底）
        self.LOG.warning("没有找到合适的处理器: %s", cleaned_content[:50])
        return "诶嘿~这个消息把我难住了捏，换个方式问问我吧~"

    def handle_msg_async(self, msg: ChatMsg) -> None:
        """
        异步处理消息

        使用线程池在后台处理消息。

        Args:
            msg: 聊天消息
        """
        _executor.submit(self._process_message, msg)

    def _process_message(self, msg: ChatMsg) -> None:
        """
        处理消息的内部方法

        Args:
            msg: 聊天消息
        """
        try:
            result = self.handler_msg(msg)

            # 如果有同步返回结果，发送出去
            if result:
                context_id = msg.chat_id if msg.from_group() else msg.sender
                at_user = msg.sender if msg.from_group() else ""
                base_client.send_text(context_id, at_user, result)

        except Exception as e:
            self.LOG.exception("处理消息失败: %s", e)
            # 尝试发送错误提示
            try:
                context_id = msg.chat_id if msg.from_group() else msg.sender
                at_user = msg.sender if msg.from_group() else ""
                base_client.send_text(context_id, at_user, "呜呜~出了点小状况，稍后再试试吧~")
            except Exception:
                self.LOG.exception("发送错误提示失败")
