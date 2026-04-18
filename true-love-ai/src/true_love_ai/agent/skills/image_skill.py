# -*- coding: utf-8 -*-
"""图像生成/分析 Skill（复用 AI 现有 image_service）"""
import logging

from true_love_ai.agent.skill_registry import register_skill

LOG = logging.getLogger("ImageSkill")


@register_skill({
    "type": "function",
    "function": {
        "name": "generate_image",
        "description": (
            "根据文字描述生成图像，或对已有图片进行图生图、擦除、替换等操作。"
            "当用户说'画一张...','生成图片...','帮我画...'时使用。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "图像描述（英文 prompt 效果更好）"
                },
                "image_path": {
                    "type": "string",
                    "description": "参考图片路径（可选，用于图生图）"
                }
            },
            "required": ["prompt"]
        }
    }
})
async def generate_image(params: dict, ctx: dict) -> str:
    prompt = params.get("prompt", "")
    image_path = params.get("image_path", "")
    receiver = ctx.get("receiver", "")
    sender = ctx.get("sender", "")
    session_id = ctx.get("session_id", "")

    if not prompt:
        return "诶嘿~请告诉我你想要什么样的图片哦~"

    try:
        from true_love_ai.services.image_service import ImageService
        service = ImageService()

        img_data = None
        if image_path:
            try:
                import base64
                with open(image_path, "rb") as f:
                    img_data = base64.b64encode(f.read()).decode()
            except Exception:
                pass

        result = await service.generate_image(
            content=prompt,
            img_data=img_data,
            wxid=session_id,
            sender=sender,
        )

        if result and result.img:
            import base64
            import uuid
            from true_love_ai.services.image_service import GEN_IMG_DIR
            from true_love_ai.agent.server_client import send_file
            file_id = uuid.uuid4().hex
            (GEN_IMG_DIR / f"{file_id}.jpg").write_bytes(base64.b64decode(result.img))
            await send_file(receiver, file_id, file_type="image")
            return "好耶~图片已生成并发送！"

        return "呜呜~图片生成失败了捏，稍后再试试吧~"
    except Exception as e:
        LOG.error("generate_image error: %s", e)
        return "呜呜~图片生成出错了捏~"


@register_skill({
    "type": "function",
    "function": {
        "name": "analyze_image",
        "description": (
            "分析图片内容，回答关于图片的问题。"
            "当用户发送图片并要求分析或提问时使用。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "关于图片的问题或分析请求"
                },
                "image_path": {
                    "type": "string",
                    "description": "图片文件路径"
                }
            },
            "required": ["question", "image_path"]
        }
    }
})
async def analyze_image(params: dict, ctx: dict) -> str:
    question = params.get("question", "请分析这张图片")
    image_path = params.get("image_path", "")
    session_id = ctx.get("session_id", "")
    sender = ctx.get("sender", "")

    if not image_path:
        return "诶嘿~请提供图片路径哦~"

    try:
        import base64
        with open(image_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode()

        from true_love_ai.services.image_service import ImageService
        result = await ImageService().analyze_image(
            content=question,
            img_data=img_data,
            wxid=session_id,
            sender=sender,
        )
        return result or "呜呜~图片分析失败了捏~"
    except Exception as e:
        LOG.error("analyze_image error: %s", e)
        return "呜呜~图片分析出错了捏~"
