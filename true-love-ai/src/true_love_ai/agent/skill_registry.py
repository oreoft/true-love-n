# -*- coding: utf-8 -*-
"""
Skill Registry

管理所有 AI 侧 skill 的注册和执行。
每个 skill 是一个 async callable，接收 (params: dict, ctx: dict) → str。
"""

import logging
from typing import Callable, Awaitable

LOG = logging.getLogger("SkillRegistry")

# {name: {"schema": {...}, "handler": async fn}}
_skills: dict[str, dict] = {}


def register_skill(schema: dict):
    """
    装饰器：注册一个 skill。

    schema 格式（OpenAI function tool schema）：
    {
        "type": "function",
        "function": {
            "name": "skill_name",
            "description": "...",
            "parameters": {...}
        }
    }

    被装饰的函数签名：async def fn(params: dict, ctx: dict) -> str
    """
    def decorator(fn: Callable[[dict, dict], Awaitable[str]]):
        name = schema["function"]["name"]
        _skills[name] = {"schema": schema, "handler": fn}
        LOG.debug("Registered skill: %s", name)
        return fn
    return decorator


def get_all_tool_schemas() -> list[dict]:
    """获取所有已注册 skill 的 tool schema 列表（供 LLM tools 参数使用）"""
    import copy
    schemas = []
    for s in _skills.values():
        schema = copy.deepcopy(s["schema"])
        params = schema.get("function", {}).get("parameters", {})
        # Gemini 不接受 properties: {}，空时删掉该字段
        if isinstance(params.get("properties"), dict) and not params["properties"]:
            params.pop("properties", None)
            params.pop("required", None)
        schemas.append(schema)
    return schemas


async def execute(name: str, params: dict, ctx: dict) -> str:
    """执行指定 skill"""
    skill = _skills.get(name)
    if not skill:
        return f"[未知 skill: {name}]"
    return await skill["handler"](params, ctx)


def list_skills() -> list[str]:
    return list(_skills.keys())
