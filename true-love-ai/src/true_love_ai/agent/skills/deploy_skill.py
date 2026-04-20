# -*- coding: utf-8 -*-
"""GitHub Actions 部署 Skill"""
import json
import logging

from true_love_ai.agent.skill_registry import register_skill

LOG = logging.getLogger("DeploySkill")


@register_skill({
    "type": "function",
    "function": {
        "name": "deploy",
        "description": (
            "触发 GitHub Actions 生产环境部署。支持 prod1 和 prod2 两套环境。"
            "当用户说'部署prod1'、'发布prod2'、'上线prod1'等时使用。"
        ),
        "parameters": {
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
    }
})
async def deploy(params: dict, ctx: dict) -> str:
    from true_love_ai.core.config import get_config
    from true_love_ai.agent.skills.permission import require_permission
    if err := require_permission("deploy", ctx):
        return err

    cfg = get_config().github
    env = params.get("env", "").strip()
    if env not in ("prod1", "prod2"):
        return "诶嘿~部署环境只支持 prod1 或 prod2 哦~"

    num = env[-1]
    url = (
        f"https://api.github.com/repos/oreoft/overlc-backend-n/"
        f"actions/workflows/ci-prod-publish{num}.yml/dispatches"
    )
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {cfg.token}",
        "Content-Type": "application/json",
    }
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, headers=headers, content=json.dumps({"ref": "master"}))
        LOG.info("deploy %s response: %s", env, resp.status_code)
        return f"好耶~{env} 部署命令已发送，等待 GitHub Actions 执行结果吧~"
    except Exception as e:
        LOG.error("deploy error: %s", e)
        return "呜呜~部署命令发送失败了捏，稍后再试试吧~"
