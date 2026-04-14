# -*- coding: utf-8 -*-
"""
Skill 基础定义：SkillContext 和 BaseSkillImpl
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SkillContext:
    """Skill 执行时的上下文"""
    wxid: str      # 会话 ID（群聊=chatroom ID，私聊=sender）
    sender: str    # 发送者昵称
    group_id: str  # 信息孤岛边界（群聊=wxid，私聊=sender）
    is_group: bool = False # 是否来自群聊


class BaseSkillImpl(ABC):
    """Server 侧 Skill 实现基类"""

    # --- 由子类声明，同时也是暴露给 AI 的 schema ---
    name: str           # 唯一标识（与 AI 侧 schema name 对应）
    description: str    # 自然语言描述（供 LLM 理解）
    allow_users: list = field(default_factory=list)   # 空=所有人可用
    only_private: bool = False   # True=仅私聊可用

    def parameters_schema(self) -> dict:
        """返回 OpenAI function parameters schema，子类可覆盖"""
        return {"type": "object", "properties": {}, "required": []}

    def to_tool_schema(self) -> dict:
        """导出为 OpenAI function call tool 格式，供 AI 拉取"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema(),
            }
        }

    def check_permission(self, ctx: SkillContext) -> str | None:
        """
        权限检查，返回 None 表示通过，返回字符串表示拒绝原因。
        子类可覆盖扩展权限逻辑。
        """
        if self.only_private and ctx.wxid != ctx.sender:
            return "该功能只能在私聊中使用哦~"
        if self.allow_users and ctx.sender not in self.allow_users:
            return "该功能您没有使用权限哦~"
        return None

    @abstractmethod
    def execute(self, params: dict, ctx: SkillContext) -> str:
        """执行 skill，返回回复文本"""
        ...
