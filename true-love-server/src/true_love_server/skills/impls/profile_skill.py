# -*- coding: utf-8 -*-
"""用户画像管理 Skill"""
import logging

from ..base_skill import BaseSkillImpl, SkillContext
from ..executor import register_skill
from ...memory.memory_manager import upsert_user_memory
from ...memory.user_memory_repository import ALLOWED_KEYS

LOG = logging.getLogger("ProfileSkill")

@register_skill
class SaveProfileSkill(BaseSkillImpl):
    name = "save_user_profile"
    description = (
        "保存用户的个人属性和画像信息到底层系统，使其永久生效。"
        "当用户主动陈述与自身相关的客观事实（例如：【他在哪个时区】、所属职业、个人喜好等）要求你记住时，"
        "【最高指令约束】：你必须放弃使用 type_answer 进行闲聊回复，而应该立刻、仅调用本 save_user_profile 技能进行数据入库！"
        "系统会在技能执行完毕后替你用萌妹语气给用户完美的闲聊回答，这部分不需要你操心！如果不调此技能，数据将永远丢失！"
    )
    allow_users = []
    only_private = False

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": f"属性类别键名。常用键名严格限定为以下之一: {', '.join(ALLOWED_KEYS)}",
                    "enum": list(ALLOWED_KEYS)
                },
                "value": {
                    "type": "string",
                    "description": "具体的属性值。如果 key 是 timezone，请务必将其转换为标准的 IANA 时区大洲/城市格式（例如 America/Chicago, Asia/Shanghai, Europe/London 等），绝不要使用中文或字母缩写表示时区值。"
                }
            },
            "required": ["key", "value"]
        }

    def execute(self, params: dict, ctx: SkillContext) -> str:
        key = params.get("key")
        value = params.get("value")
        
        if not key or not value:
            return "呜呜~保存画像失败啦，必须要告诉我属性类别和具体的值哦！"
            
        try:
            # 存入底层数据库
            upsert_user_memory(ctx.group_id, ctx.sender, [{"key": key, "value": value}], source="profile_skill")
            LOG.info("用户 [%s] 主动保存了画像信息: %s = %s", ctx.sender, key, value)
            
            # 返回友好语境，给 LLM 继续包装
            if key == "timezone":
                return f"好的，我已经帮你把你的系统专属时区永久设置为 {value} 啦！以后有关时间的推算我都不会出错咯~"
            else:
                return f"好哒，我已经把你 {value} 的专属特征拿小本本牢牢记在数据库里啦！"
        except Exception as e:
            LOG.error("存入画像失败: %s", e)
            return "呀，系统小本本卡住了，没能帮你记下来呢，稍后再试一下吧~"
