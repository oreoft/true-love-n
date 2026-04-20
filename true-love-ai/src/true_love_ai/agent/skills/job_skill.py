# -*- coding: utf-8 -*-
"""手动触发定时任务 Skill"""
import logging

from true_love_ai.agent.skill_registry import register_skill
from true_love_ai.agent.server_client import _async_post

LOG = logging.getLogger("JobSkill")

_JOBS = [
    "notice_moyu_schedule",
    "notice_usa_moyu_schedule",
    "download_moyu_file",
    "download_zao_bao_file",
    "notice_test",
    "notice_mei_yuan",
    "notice_library_schedule",
    "notice_ao_yuan_schedule",
]


@register_skill({
    "type": "function",
    "function": {
        "name": "run_job",
        "description": (
            "手动触发服务器定时任务（用于测试）。"
            f"可用任务：{', '.join(_JOBS)}。"
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

    result = await _async_post("/admin/job/run", {"job_name": job_name}, timeout=10.0)
    if result.get("code") == 0:
        return f"好的~已触发任务 {job_name}，后台执行中~"
    return f"触发失败：{result.get('message', result)}"
