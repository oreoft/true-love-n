# -*- coding: utf-8 -*-
"""
Skill 权限管理

查找顺序：
1. skill_permissions[skill_name] 有配置 → 用该列表
2. 没有配置 → 走 skill_permissions["default"]
3. default 也没有 → 所有人可用
"""
from true_love_ai.core.config import get_config


def require_permission(skill_name: str, ctx: dict) -> str | None:
    """
    检查调用者是否有权限执行指定 skill。

    Returns:
        None 表示有权限；非 None 为错误提示，直接 return 给用户。
    """
    sender = ctx.get("sender", "")
    perms: dict[str, list[str]] = get_config().skill_permissions

    allowed = perms.get(skill_name)
    if allowed is None:
        allowed = perms.get("default")

    if allowed is not None and sender not in allowed:
        return "诶嘿~这个功能你没有权限使用哦~"
    return None
