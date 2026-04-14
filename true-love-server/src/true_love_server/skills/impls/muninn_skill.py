# -*- coding: utf-8 -*-
"""Muninn CDK 生成 Skill"""
import logging

import requests

from ..base_skill import BaseSkillImpl, SkillContext
from ..executor import register_skill
from ...core import Config

LOG = logging.getLogger("MuninnSkill")


@register_skill
class MuninnCdkSkill(BaseSkillImpl):
    name = "muninn_cdk"
    description = (
        "生成 Muninn 会员 CDK 激活码。"
        "需要指定会员等级（如 pro、basic）和有效天数。"
        "当用户说'生成muninn cdk'、'生成会员码'等时使用。"
    )
    only_private = False

    def __init__(self):
        config = Config()
        self.allow_users = config.MUNINN.get("allow_user", [])
        self.api_base_url = config.MUNINN.get("api_base_url", "")
        self.admin_token = config.MUNINN.get("admin_token", "")

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "level": {
                    "type": "string",
                    "description": "会员等级，如：pro、basic"
                },
                "days": {
                    "type": "integer",
                    "description": "有效天数，如：30、90、365"
                }
            },
            "required": ["level", "days"]
        }

    def execute(self, params: dict, ctx: SkillContext) -> str:
        if not self.api_base_url or not self.admin_token:
            return "呜呜~Muninn 配置不完整，请联系管理员~"

        level = params.get("level", "").strip()
        try:
            days = int(params.get("days", 0))
        except (TypeError, ValueError):
            return "呜呜~天数必须是数字哦~"

        if not level or days <= 0:
            return "诶嘿~请指定会员等级和有效天数哦，例如：等级 pro，30天~"

        try:
            url = f"{self.api_base_url}/membership/admin/cdk/generate"
            resp = requests.post(
                url,
                headers={"X-Admin-Token": self.admin_token, "Content-Type": "application/json"},
                json={"level": level, "duration_days": days, "count": 1},
                timeout=30,
            )
            if resp.status_code == 200:
                result = resp.json()
                if result.get("code") == 0:
                    codes = result.get("data", {}).get("codes", [])
                    if codes:
                        return (
                            f"✅ Muninn CDK 生成成功！\n\n"
                            f"等级: {level}\n天数: {days}天\nCDK: {codes[0]}\n\n请妥善保管 CDK 码~"
                        )
                    return "呜呜~生成失败了，API 返回的 CDK 列表为空~"
                return f"呜呜~生成失败了: {result.get('message', '未知错误')}"
            return f"呜呜~生成失败了，API 返回状态码: {resp.status_code}"
        except requests.exceptions.Timeout:
            return "呜呜~生成失败了，API 调用超时~"
        except Exception as e:
            LOG.error("muninn_cdk error: %s", e)
            return f"呜呜~生成失败了，发生未知错误~"
