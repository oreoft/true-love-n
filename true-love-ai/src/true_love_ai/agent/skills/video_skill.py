# -*- coding: utf-8 -*-
"""视频生成 Skill（复用 AI 现有 video_service）"""
import logging

from true_love_ai.agent.skill_registry import register_skill

LOG = logging.getLogger("VideoSkill")


@register_skill({
    "type": "function",
    "function": {
        "name": "generate_video",
        "description": (
            "根据文字描述或图片生成短视频。"
            "当用户说'生成视频...','帮我做一个视频...'时使用。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "视频描述（英文 prompt 效果更好）"
                }
            },
            "required": ["prompt"]
        }
    }
})
async def generate_video(params: dict, ctx: dict) -> str:
    prompt = params.get("prompt", "")
    receiver = ctx.get("receiver", "")
    sender = ctx.get("sender", "")
    session_id = ctx.get("session_id", "")

    if not prompt:
        return "诶嘿~请告诉我你想要什么样的视频哦~"

    try:
        from true_love_ai.services.video_service import VideoService
        result = await VideoService().generate_video(
            content=prompt,
            img_data_list=[],
            wxid=session_id,
            sender=sender,
        )

        if result and result.video_path:
            from true_love_ai.agent.server_client import send_file
            await send_file(receiver, result.video_path, file_type="video")
            return "好耶~视频已生成并发送！"

        return "呜呜~视频生成失败了捏，稍后再试试吧~"
    except Exception as e:
        LOG.error("generate_video error: %s", e)
        return "呜呜~视频生成出错了捏~"
