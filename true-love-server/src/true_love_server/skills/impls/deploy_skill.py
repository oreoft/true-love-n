# -*- coding: utf-8 -*-
"""GitHub Actions 部署 Skill"""
import json
import logging

import requests

from ..base_skill import BaseSkillImpl, SkillContext
from ..executor import register_skill
from ...core import Config

LOG = logging.getLogger("DeploySkill")


@register_skill
class DeploySkill(BaseSkillImpl):
    name = "deploy"
    description = (
        "触发 GitHub Actions 生产环境部署。"
        "支持 prod1 和 prod2 两套环境。"
        "当用户说'部署prod1'、'发布prod2'、'上线prod1'等时使用。"
    )
    only_private = False

    def __init__(self):
        config = Config()
        self.allow_users = config.GITHUB.get("allow_user", [])
        self.token = config.GITHUB.get("token", "")

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "env": {
                    "type": "string",
                    "enum": ["prod1", "prod2"],
                    "description": "部署环境：prod1 或 prod2"
                }
            },
            "required": ["env"]
        }

    def execute(self, params: dict, ctx: SkillContext) -> str:
        env = params.get("env", "").strip()
        if env not in ("prod1", "prod2"):
            return "诶嘿~部署环境只支持 prod1 或 prod2 哦~"

        num = env[-1]  # "1" or "2"
        url = (
            f"https://api.github.com/repos/oreoft/overlc-backend-n/"
            f"actions/workflows/ci-prod-publish{num}.yml/dispatches"
        )
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {self.token}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(url, headers=headers, data=json.dumps({"ref": "master"}), timeout=15)
            LOG.info("deploy %s response: %s", env, resp.status_code)
            return f"好耶~{env} 部署命令已发送，等待 GitHub Actions 执行结果吧~"
        except Exception as e:
            LOG.error("deploy error: %s", e)
            return "呜呜~部署命令发送失败了捏，稍后再试试吧~"
