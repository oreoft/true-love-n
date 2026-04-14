# -*- coding: utf-8 -*-
"""配置重载 Skill"""
import logging

from ..base_skill import BaseSkillImpl, SkillContext
from ..executor import register_skill
from ...core import Config

LOG = logging.getLogger("ConfigSkill")


@register_skill
class ReloadConfigSkill(BaseSkillImpl):
    name = "reload_config"
    description = (
        "重新加载服务配置文件，使配置修改立即生效，无需重启服务。"
        "当用户说'更新配置'、'重载配置'、'reload config'时使用。"
    )
    only_private = False

    def __init__(self):
        config = Config()
        self.allow_users = config.GITHUB.get("allow_user", [])

    def execute(self, params: dict, ctx: SkillContext) -> str:
        try:
            Config().reload()
            LOG.info("配置已重载, 操作者: %s", ctx.sender)
            return "好耶~配置已重新加载成功！"
        except Exception as e:
            LOG.error("reload_config error: %s", e)
            return f"呜呜~配置重载失败了: {e}"
