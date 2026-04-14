# -*- coding: utf-8 -*-
from .executor import skill_executor, register_skill
from .base_skill import BaseSkillImpl, SkillContext

# 导入所有实现，触发 @register_skill 装饰器注册
from .impls import (  # noqa: F401
    currency_skill,
    gold_skill,
    deploy_skill,
    muninn_skill,
    listen_skill,
    config_skill,
    reminder_skill,
    profile_skill,
)

__all__ = ["skill_executor", "register_skill", "BaseSkillImpl", "SkillContext"]
