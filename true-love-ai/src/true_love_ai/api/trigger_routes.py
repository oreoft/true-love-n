# -*- coding: utf-8 -*-
"""
Trigger Routes

Server 收到 Base 消息后，fire-and-forget POST 到这里，AI 启动 Agent Loop 处理。
"""

import logging

from fastapi import APIRouter, BackgroundTasks

from true_love_ai.api.deps import verify_token
from true_love_ai.models.response import APIResponse

LOG = logging.getLogger("TriggerRoutes")

trigger_router = APIRouter()


@trigger_router.post("/trigger")
async def trigger(request: dict, background_tasks: BackgroundTasks):
    """
    消息触发入口

    Server 在收到 Base 消息并完成存储后，异步 POST 到此接口。
    本接口立即返回 200，后台启动 Agent Loop 处理。

    Body:
        - token: 鉴权 token
        - msg:   ChatMsg.to_dict() 格式的消息字典
    """
    if not verify_token(request.get("token", "")):
        return APIResponse.token_error()

    msg = request.get("msg")
    if not msg:
        return APIResponse.error("msg 不能为空")

    LOG.info("收到 trigger: sender=%s, type=%s, is_group=%s",
             msg.get("sender"), msg.get("msg_type"), msg.get("is_group"))

    # 触发 skill 模块加载（保证 skills 已注册）
    from true_love_ai.agent.skills import ensure_skills_loaded
    ensure_skills_loaded()

    # fire-and-forget
    from true_love_ai.agent.agent_loop import get_agent_loop
    background_tasks.add_task(_run_agent, msg)

    return APIResponse.success(None)


async def _run_agent(msg: dict) -> None:
    """后台执行 Agent Loop，捕获所有异常避免影响服务"""
    try:
        from true_love_ai.agent.agent_loop import get_agent_loop
        await get_agent_loop().run(msg)
    except Exception as e:
        LOG.exception("Agent Loop 执行异常: sender=%s, err=%s", msg.get("sender"), e)
