# -*- coding: utf-8 -*-
"""手动触发定时任务 Skill"""
import logging

from true_love_ai.agent.skill_registry import register_skill
from true_love_ai.agent.server_client import _async_post

LOG = logging.getLogger("JobSkill")

_JOBS = [
    "notice_moyu_schedule",
    "notice_usa_moyu_schedule",
]


@register_skill({
    "type": "function",
    "function": {
        "name": "run_job",
        "description": (
            "立即执行服务器上某个任务名下的所有定时任务（用于测试），推给这些定时任务里配置的群。"
            f"可用任务：{', '.join(_JOBS)}（国内摸鱼、美国摸鱼）。"
            "当用户说'执行job xxx'、'触发任务 xxx'、'跑一下 xxx' 等时使用。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "job_name": {
                    "type": "string",
                    "enum": _JOBS,
                    "description": "要触发的任务名称"
                }
            },
            "required": ["job_name"]
        }
    }
})
async def run_job(params: dict, ctx: dict) -> str:
    job_name = params.get("job_name", "").strip()
    if job_name not in _JOBS:
        return f"未知任务：{job_name}，可选：{', '.join(_JOBS)}"

    result = await _async_post("/action/job/run", {"job_name": job_name}, timeout=10.0)
    if result.get("code") == 0:
        count = (result.get("data") or {}).get("tasks", 0)
        if not count:
            return f"{job_name} 还没有配置定时任务，去后台的定时任务页加一个吧~"
        return f"好的~已触发 {job_name} 的 {count} 个定时任务，后台执行中~"
    return f"触发失败：{result.get('message', result)}"
