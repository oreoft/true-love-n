# -*- coding: utf-8 -*-
"""监听管理 Skill（仅限 master 私聊）"""
import logging

from ..base_skill import BaseSkillImpl, SkillContext
from ..executor import register_skill
from ...core import Config
from ...services.listen_manager import get_listen_manager

LOG = logging.getLogger("ListenSkill")


@register_skill
class ListenManageSkill(BaseSkillImpl):
    name = "listen_manage"
    description = (
        "管理微信监听列表，支持查询、新增、删除、刷新监听对象。"
        "仅限管理员私聊使用。"
        "当管理员说'查看监听'、'新增监听xxx'、'删除监听xxx'、'刷新监听'时使用。"
    )
    only_private = True  # 仅私聊

    def __init__(self):
        config = Config()
        master = config.BASE_SERVER.get("master_name", "")
        # 只有 master_name 可以使用
        self.allow_users = [master] if master else []

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["query", "add", "remove", "refresh"],
                    "description": "操作类型：query=查询列表, add=新增, remove=删除, refresh=刷新"
                },
                "target": {
                    "type": "string",
                    "description": "监听对象名称（add/remove 时必填）"
                }
            },
            "required": ["action"]
        }

    def execute(self, params: dict, ctx: SkillContext) -> str:
        action = params.get("action", "").strip()
        target = params.get("target", "").strip()
        mgr = get_listen_manager()

        if action == "query":
            lst = mgr.get_listen_list()
            if not lst:
                return "诶嘿~当前没有监听任何对象哦~"
            items = "\n".join(f"  {i+1}. {n}" for i, n in enumerate(lst))
            return f"当前监听列表 ({len(lst)}个):\n{items}"

        if action == "add":
            if not target:
                return "诶嘿~请告诉我要新增的监听对象名称哦~"
            result = mgr.add_listen(target)
            if result.get("success"):
                return f"好耶~添加监听成功: {target}"
            return f"呜呜~添加监听失败: {result.get('message', '未知错误')}"

        if action == "remove":
            if not target:
                return "诶嘿~请告诉我要删除的监听对象名称哦~"
            result = mgr.remove_listen(target)
            if result.get("success"):
                return f"好耶~删除监听成功: {target}"
            return f"呜呜~删除监听失败: {result.get('message', '未知错误')}"

        if action == "refresh":
            data = mgr.refresh_listen()
            total = data.get("total", 0)
            if total == 0:
                return "诶嘿~当前没有监听任何对象哦~"
            success_count = data.get("success_count", 0)
            fail_count = data.get("fail_count", 0)
            status = "全部正常 ✓" if fail_count == 0 else f"部分失败 ✗ ({fail_count}个)"
            return (
                f"监听列表刷新完成:\n"
                f"  总数: {total}个\n"
                f"  成功: {success_count}个，失败: {fail_count}个\n"
                f"  状态: {status}"
            )

        return "诶嘿~不支持该操作，支持：query / add / remove / refresh"
