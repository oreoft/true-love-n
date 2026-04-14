# -*- coding: utf-8 -*-
"""提醒管理 Skill"""
import logging
from datetime import datetime
import dateutil.parser

from ..base_skill import BaseSkillImpl, SkillContext
from ..executor import register_skill
from ...services import base_client
from ...services.scheduler_service import scheduler

LOG = logging.getLogger("ReminderSkill")

def trigger_reminder(target: str, at: str, content: str):
    """到达时间后触发推送"""
    LOG.info("执行定时提醒: 给 %s 推送 [%s]", target, content)
    base_client.send_text(target, at, f"⏰ 【提醒功能】：\n\n{content}")


@register_skill
class SetReminderSkill(BaseSkillImpl):
    name = "set_reminder"
    description = (
        "为用户设定一个未来的定时提醒任务。例如'十分钟后提醒我关火'或'明天中午提醒我开会'。"
        "系统已根据用户的时区换算了当地时间，请务必根据其当地时间推演出标准 ISO-8601 触达时间传入。"
    )
    allow_users = []
    only_private = False

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "target_time_iso": {
                    "type": "string",
                    "description": "换算成目标的标准 ISO-8601 时刻字符串。包含时区信息（如 2026-04-14T10:30:00+08:00）。如果推导失败，给一个合理的近似绝对时间。"
                },
                "content": {
                    "type": "string",
                    "description": "要提醒的具体内容事件。应以直接的命令语气描述，如'关火'、'去开会'。"
                }
            },
            "required": ["target_time_iso", "content"]
        }

    def execute(self, params: dict, ctx: SkillContext) -> str:
        iso_str = params.get("target_time_iso")
        content = params.get("content")

        if not iso_str or not content:
            return "呜呜~设置提醒需要确切的时间点和内容哦！能不能再详细说明一下捏？"

        try:
            # 解析日期
            dt = dateutil.parser.isoparse(iso_str)
            # 兼容时间对比
            now = datetime.now(dt.tzinfo)
            if dt <= now:
                return f"诶嘿？解析出的时间 {iso_str} 好像在过去啦！是不是时区没对上呢？"
            
            # 添加调度任务
            # group_id 标识所在聊天窗口位置。如果是群聊就是目标群，私聊就是对方。
            job_id = f"reminder_{ctx.group_id}_{int(now.timestamp())}"
            at_user = ctx.sender if ctx.is_group else ""
            scheduler.add_job(
                trigger_reminder,
                'date',
                run_date=dt,
                args=[ctx.group_id, at_user, content],
                id=job_id
            )
            tz_display = dt.tzname() or f"UTC{dt.strftime('%z')}"
            return f"好耶~设置提醒成功！会在 {dt.strftime('%m-%d %H:%M:%S')} ({tz_display}) 这个时间准时提醒你哦~"
        except Exception as e:
            LOG.error("设置提醒时间解析失败 [%s]: %s", iso_str, e)
            return f"呜呜~设置提醒发生错误，你给的时间格式不对捏 ({iso_str})，重试一次吧~"


@register_skill
class QueryReminderSkill(BaseSkillImpl):
    name = "query_reminder"
    description = "查询当前用户所在会话所有未执行的定时提醒作业。"
    allow_users = []
    only_private = False

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, params: dict, ctx: SkillContext) -> str:
        jobs = scheduler.get_jobs()
        my_jobs = []
        for j in jobs:
            # 检查 args: [target, at, content]
            if j.args and len(j.args) >= 3 and j.args[0] == ctx.group_id:
                # 进一步区分属于谁
                if j.args[1] == "" or j.args[1] == ctx.sender:
                    my_jobs.append(f"【{j.id}】执行时间: {j.next_run_time.strftime('%m-%d %H:%M')}，内容: {j.args[2]}")
        
        if not my_jobs:
            return "暂未查到你在这个聊天中的待办提醒记录哦~"
        return "查询到以下未执行的提醒任务：\n" + "\n".join(my_jobs)

@register_skill
class DeleteReminderSkill(BaseSkillImpl):
    name = "delete_reminder"
    description = "取消或删除指定的定时提醒任务。"
    allow_users = []
    only_private = False

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "string",
                    "description": "要取消的提醒作业ID。通常需要通过先调用查询接口拿到ID列表。"
                }
            },
            "required": ["job_id"]
        }

    def execute(self, params: dict, ctx: SkillContext) -> str:
        job_id = params.get("job_id")
        if not job_id:
            return "呜呜~不提供需要删除的任务指令ID的话，我不知道你要删哪个呢~"
        
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
            return f"好耶~已成功为您删除对应的提醒记录！"
        return "呜呜~没找到指定的提醒任务，是不是已经过期或者已被删除啦？"
