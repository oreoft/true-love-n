# -*- coding: utf-8 -*-
"""模型管理 Skill（管理员专用）"""
import logging

from true_love_ai.agent.skill_registry import register_skill
from true_love_ai.agent.skills.permission import require_permission

LOG = logging.getLogger("ModelSkill")


@register_skill({
    "type": "function",
    "function": {
        "name": "list_models",
        "description": "查看当前所有类别的模型配置。当用户问'现在用的什么模型'、'模型配置是什么'时使用。",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }
})
async def list_models(params: dict, ctx: dict) -> str:
    require_permission("list_models", ctx)
    from true_love_ai.core.model_registry import get_model_registry
    models = get_model_registry().all()
    lines = ["当前模型配置："]
    for category, entries in models.items():
        for key, value in entries.items():
            lines.append(f"  {category}.{key} = {value}")
    return "\n".join(lines)


@register_skill({
    "type": "function",
    "function": {
        "name": "set_model",
        "description": (
            "动态修改指定类别的模型，修改后立即生效并持久化，重启后仍保留。"
            "当用户说'把聊天模型换成xxx'、'图片生成改用xxx'时使用。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["chat", "compress", "vision", "image", "video"],
                    "description": "模型类别",
                },
                "key": {
                    "type": "string",
                    "description": "类别下的 key，如 openai / claude / gemini 等",
                },
                "value": {
                    "type": "string",
                    "description": "完整的 LiteLLM 模型字符串，如 openai/gpt-5.5 或 openai/claude/claude-4",
                },
            },
            "required": ["category", "key", "value"],
        },
    }
})
async def set_model(params: dict, ctx: dict) -> str:
    require_permission("set_model", ctx)
    category = params.get("category", "").strip()
    key = params.get("key", "").strip()
    value = params.get("value", "").strip()

    if not category or not key or not value:
        return "参数不完整，需要 category、key、value 三个参数。"

    try:
        from true_love_ai.core.model_registry import get_model_registry
        registry = get_model_registry()
        old = registry.get(category, key) if key in registry.all().get(category, {}) else "（未配置）"
        registry.set(category, key, value)
        LOG.info("模型已更新: %s.%s: %s → %s", category, key, old, value)
        return f"好的，已将 {category}.{key} 从 {old} 更新为 {value}，已持久化。"
    except Exception as e:
        LOG.error("set_model 失败: %s", e)
        return f"更新失败: {e}"
