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
            "根据文字描述生成图像。"
            "当用户说'画一张...','生成图片...','帮我画...'时使用。"
            "默认优先用 Gemini，失败自动降级 OpenAI。"
            "用户明确指定提供商（如'用openai画'）时才传 provider 参数。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "图像描述，直接使用用户的原始表达，中英文均可。"
                        "保留用户的原始意图，不要自行添加风格词、修饰词或额外细节。"
                    )
                },
                "provider": {
                    "type": "string",
                    "enum": ["gemini", "openai"],
                    "description": "生图提供商，不指定时 Gemini 优先自动降级"
                }
            },
            "required": ["prompt"]
        }
    }
})
async def generate_image(params: dict, ctx: dict) -> str:
    prompt = params.get("prompt", "")
    provider = params.get("provider")
    receiver = ctx.get("receiver", "")

    if not prompt:
        return "诶嘿~请告诉我你想要什么样的图片哦~"

    try:
        from true_love_ai.services.image_service import ImageService, GEN_IMG_DIR
        from true_love_ai.agent.server_client import send_file
        import base64
        import uuid

        result = await ImageService().generate_image(image_prompt=prompt, provider=provider)

        if result and result.img:
            file_id = uuid.uuid4().hex
            (GEN_IMG_DIR / f"{file_id}.jpg").write_bytes(base64.b64decode(result.img))
            await send_file(receiver, file_id, file_type="image")
            return "好耶~图片已生成并发送！"

        return "呜呜~图片生成失败了捏，稍后再试试吧~"
    except Exception as e:
        LOG.error("generate_image error: %s", e)
        return f"呜呜~图片生成出错了捏：{e}"


@register_skill({
    "type": "function",
    "function": {
        "name": "analyze_image",
        "description": (
            "分析图片内容，回答关于图片的问题。"
            "当用户发送图片（消息中含 [图片:...] 或 [引用图片:...]）并要求分析或提问时使用。"
            "从消息中提取图片路径（如 wx_imgs/xxx.jpg）传入 image_path。"
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
                    "description": "图片文件路径，如 wx_imgs/xxx.jpg"
                }
            },
            "required": ["question", "image_path"]
        }
    }
})
async def analyze_image(params: dict, ctx: dict) -> str:
    question = params.get("question", "请分析这张图片")
    image_path = params.get("image_path", "")

    if not image_path:
        return "诶嘿~请提供图片路径哦~"

    try:
        import base64
        from true_love_ai.agent.server_client import fetch_media_bytes
        data = await fetch_media_bytes(image_path)
        if not data:
            return "呜呜~图片获取失败了捏，可能文件不存在~"
        img_data = base64.b64encode(data).decode()

        from true_love_ai.services.image_service import ImageService
        result = await ImageService().analyze_image(
            content=question,
            img_data=img_data,
        )
        return result or "呜呜~图片分析失败了捏~"
    except Exception as e:
        LOG.error("analyze_image error: %s", e)
        return f"呜呜~图片分析出错了捏：{e}"


@register_skill({
    "type": "function",
    "function": {
        "name": "edit_image",
        "description": (
            "基于已有图片生成新图片（图生图）。"
            "当用户发送图片并说'变成...风格','修改成...','帮我把这张图...'时使用。"
            "从消息中提取 [图片:...] 或 [引用图片:...] 中的路径传入 image_path。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "原始图片路径，如 wx_imgs/xxx.jpg"
                },
                "prompt": {
                    "type": "string",
                    "description": "对新图片的描述或修改要求，如'变成水彩风格''把背景换成海边'"
                }
            },
            "required": ["image_path", "prompt"]
        }
    }
})
async def edit_image(params: dict, ctx: dict) -> str:
    image_path = params.get("image_path", "")
    prompt = params.get("prompt", "")
    receiver = ctx.get("receiver", "")

    if not image_path or not prompt:
        return "诶嘿~请提供图片路径和修改要求哦~"

    try:
        import io
        import base64
        import uuid
        import litellm
        from true_love_ai.agent.server_client import fetch_media_bytes, send_file
        from true_love_ai.core.config import get_config
        from true_love_ai.core.model_registry import get_model_registry
        from true_love_ai.services.image_service import GEN_IMG_DIR

        data = await fetch_media_bytes(image_path)
        if not data:
            return "呜呜~图片获取失败了捏，可能文件不存在~"

        cfg = get_config()
        registry = get_model_registry()
        # image_edit 接口不支持 Vertex AI，优先用 fallback（OpenAI）
        model = registry.get("image", "fallback") or registry.get("image", "default")

        response = await litellm.aimage_edit(
            model=model,
            image=io.BytesIO(data),
            prompt=prompt,
            response_format="b64_json",
            api_key=cfg.platform_key.litellm_api_key,
            api_base=cfg.platform_key.litellm_base_url,
        )

        item = response.data[0] if response.data else None
        if not item:
            return "呜呜~图片生成失败了捏~"

        img_bytes = base64.b64decode(item.b64_json) if getattr(item, "b64_json", None) else None
        if not img_bytes and getattr(item, "url", None):
            import httpx
            async with httpx.AsyncClient() as client:
                r = await client.get(item.url, timeout=60.0)
                img_bytes = r.content if r.status_code == 200 else None

        if not img_bytes:
            return "呜呜~图片生成失败了捏~"

        file_id = uuid.uuid4().hex
        (GEN_IMG_DIR / f"{file_id}.jpg").write_bytes(img_bytes)
        await send_file(receiver, file_id, file_type="image")
        return "好耶~图片已生成并发送！"

    except Exception as e:
        LOG.error("edit_image error: %s", e)
        return f"呜呜~图生图出错了捏：{e}"
