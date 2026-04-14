# -*- coding: utf-8 -*-
"""
Skill 注册表 & 执行器

所有 Skill 实现通过 @register_skill 装饰器注册到全局 skill_registry。
"""
import logging
from typing import Type

from .base_skill import BaseSkillImpl, SkillContext

LOG = logging.getLogger("SkillExecutor")


class SkillExecutor:
    """
    Skill 执行器（单例）

    职责：
    - 管理所有已注册的 SkillImpl
    - 权限校验
    - 统一执行入口
    - 导出 tool schemas 给 AI 服务拉取
    """

    def __init__(self):
        self._skills: dict[str, BaseSkillImpl] = {}

    def register(self, skill: BaseSkillImpl) -> None:
        self._skills[skill.name] = skill
        LOG.info("注册 skill: %s", skill.name)

    def execute(self, name: str, params: dict, ctx: SkillContext) -> str:
        """
        执行指定 skill。

        Args:
            name:   skill 唯一标识
            params: LLM 提取的参数字典
            ctx:    执行上下文（wxid/sender/group_id）

        Returns:
            回复文本
        """
        skill = self._skills.get(name)
        if not skill:
            LOG.warning("未找到 skill: %s，已注册: %s", name, list(self._skills.keys()))
            return f"诶嘿~没有找到这个功能呢({name})~"

        deny_msg = skill.check_permission(ctx)
        if deny_msg:
            return deny_msg

        try:
            LOG.info("执行 skill: %s, params=%s, sender=%s", name, params, ctx.sender)
            return skill.execute(params, ctx)
        except Exception as e:
            LOG.error("skill %s 执行失败: %s", name, e, exc_info=True)
            return "呜呜~执行出了点问题，稍后再试试吧~"

    def all_tool_schemas(self) -> list[dict]:
        """导出所有 skill 的 tool schema，供 AI 服务拉取"""
        return [s.to_tool_schema() for s in self._skills.values()]

    def list_names(self) -> list[str]:
        return list(self._skills.keys())


# 全局单例
skill_executor = SkillExecutor()


def register_skill(cls: Type[BaseSkillImpl]) -> Type[BaseSkillImpl]:
    """
    Skill 注册装饰器

    用法：
        @register_skill
        class MyCoolSkill(BaseSkillImpl):
            name = "my_cool_skill"
            ...
    """
    skill_executor.register(cls())
    return cls
