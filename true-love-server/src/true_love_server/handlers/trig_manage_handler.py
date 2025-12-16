# -*- coding: utf-8 -*-
"""
Trigger Manage Handler - 管理触发处理器

处理各种管理任务，如监听管理等。
"""

import logging

from .. import Config
from ..services import base_client

LOG = logging.getLogger("TrigManageHandler")


class TrigManageHandler:
    """管理触发处理器"""

    def run(self, question: str, sender: str) -> str:
        """
        处理管理命令
        
        Args:
            question: 用户输入的问题，格式如 "$管理监听 查询" 或 "$管理监听 新增-xxx"
            
        Returns:
            处理结果
        """
        # 移除 $管理 前缀，获取子类命令
        cmd = question.replace("$管理", "").strip()
        if Config().BASE_SERVER.get("master_name") != sender:
            return "只有管理员才能使用管理命令哦"

        if not cmd:
            return self._get_main_help()

        # 监听管理
        if cmd.startswith("监听"):
            return self._handle_listen(cmd)

        # 未来可扩展其他管理类型
        # if cmd.startswith("配置"):
        #     return self._handle_config(cmd)

        return self._get_main_help()

    def _handle_listen(self, cmd: str) -> str:
        """
        处理监听管理命令
        
        Args:
            cmd: 命令字符串，如 "监听 查询" 或 "监听 新增-xxx"
        """
        # 移除 "监听" 前缀，获取具体操作
        action = cmd.replace("监听", "").strip()

        if not action:
            return self._get_listen_help()

        # 查询监听列表
        if "查询" in action or "列表" in action:
            return self._query_listen_list()

        # 新增/添加监听
        if "新增" in action or "添加" in action:
            return self._add_listen(action)

        # 删除/移除监听
        if "删除" in action or "移除" in action:
            return self._remove_listen(action)

        return self._get_listen_help()

    def _query_listen_list(self) -> str:
        """查询所有监听对象"""
        LOG.info("开始查询监听列表")
        result = base_client.get_listen_list()
        if result is None:
            return "查询监听列表失败，请稍后重试"
        if not result:
            return "当前没有监听任何对象"

        # 格式化输出
        listen_list = "\n".join([f"  {i + 1}. {name}" for i, name in enumerate(result)])
        return f"当前监听列表 ({len(result)}个):\n{listen_list}"

    def _add_listen(self, action: str) -> str:
        """
        添加监听对象
        
        Args:
            action: 操作字符串，如 "新增-xxx" 或 "添加-xxx"
        """
        # 只拆分第一个 -，因为监听名称本身可能包含 -
        parts = action.split("-", 1)
        if len(parts) < 2 or not parts[1].strip():
            return "请指定要添加的监听对象，格式: $管理监听 新增-监听名称"

        chat_name = parts[1].strip()
        LOG.info(f"开始添加监听: {chat_name}")

        success, msg = base_client.add_listen(chat_name)
        if success:
            return f"添加监听成功: {chat_name}"
        return f"添加监听失败: {msg}"

    def _remove_listen(self, action: str) -> str:
        """
        删除监听对象
        
        Args:
            action: 操作字符串，如 "删除-xxx" 或 "移除-xxx"
        """
        # 只拆分第一个 -，因为监听名称本身可能包含 -
        parts = action.split("-", 1)
        if len(parts) < 2 or not parts[1].strip():
            return "请指定要删除的监听对象，格式: $管理监听 删除-监听名称"

        chat_name = parts[1].strip()
        LOG.info(f"开始删除监听: {chat_name}")

        success, msg = base_client.remove_listen(chat_name)
        if success:
            return f"删除监听成功: {chat_name}"
        return f"删除监听失败: {msg}"

    @staticmethod
    def _get_main_help() -> str:
        """获取管理主帮助信息"""
        return """管理命令使用说明:
  $管理监听 - 监听对象管理"""

    @staticmethod
    def _get_listen_help() -> str:
        """获取监听管理帮助信息"""
        return """监听管理使用说明:
  $管理监听 查询 - 查看所有监听对象
  $管理监听 新增-监听名称 - 添加监听对象
  $管理监听 添加-监听名称 - 添加监听对象
  $管理监听 删除-监听名称 - 删除监听对象
  $管理监听 移除-监听名称 - 删除监听对象"""
