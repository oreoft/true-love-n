# -*- coding: utf-8 -*-
"""用户画像管理 Skill（直接读写 AI 本地 SQLite）"""
import logging

from true_love_ai.agent.skill_registry import register_skill
from true_love_ai.memory.user_memory_repository import ALLOWED_KEYS

LOG = logging.getLogger("ProfileSkill")


@register_skill({
    "type": "function",
    "function": {
        "name": "save_user_profile",
        "description": (
            "保存用户的个人属性和画像信息到底层系统，使其永久生效。"
            "当用户主动陈述与自身相关的客观事实（例如：【他在哪个时区】、所属职业、个人喜好等）要求你记住时，"
            "【最高指令约束】：你必须放弃使用普通回复，而应该立刻、仅调用本 save_user_profile 技能进行数据入库！"
            "如果不调此技能，数据将永远丢失！"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": f"属性类别键名，严格限定为以下之一: {', '.join(ALLOWED_KEYS)}",
                    "enum": list(ALLOWED_KEYS)
                },
                "value": {
                    "type": "string",
                    "description": (
                        "具体的属性值。如果 key 是 timezone，请务必转换为标准的 IANA 时区格式"
                        "（如 America/Chicago, Asia/Shanghai），绝不要使用中文或缩写。"
                    )
                }
            },
            "required": ["key", "value"]
        }
    }
})
async def save_user_profile(params: dict, ctx: dict) -> str:
    key = params.get("key", "")
    value = params.get("value", "")

    if not key or not value:
        return "呜呜~保存画像失败啦，必须要告诉我属性类别和具体的值哦！"

    if key == "timezone":
        try:
            import zoneinfo
            zoneinfo.ZoneInfo(value)
        except Exception:
            return (
                f"呀，时区格式不太对捏，必须是标准城市格式（比如 America/Chicago 或 Asia/Shanghai），"
                f"你发的是「{value}」，请重新告诉我正确的名称哦~"
            )

    group_id = ctx.get("session_id", "")
    sender = ctx.get("sender", "")

    try:
        from true_love_ai.memory.memory_manager import upsert_user_memory
        upsert_user_memory(group_id, sender, [{"key": key, "value": value}], source="profile_skill")
        LOG.info("用户 [%s] 保存画像: %s = %s", sender, key, value)

        if key == "timezone":
            return f"好的，我已经把你的时区永久设置为 {value} 啦！以后有关时间的推算都会按这个来哦~"
        return f"好哒，我已经把你 {value} 的专属特征记在数据库里啦！"
    except Exception as e:
        LOG.error("存入画像失败: %s", e)
        return "呀，系统小本本卡住了，没能帮你记下来呢，稍后再试一下吧~"
