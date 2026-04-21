# -*- coding: utf-8 -*-
"""文件分析 Skill - 直接把文件作为 multimodal 内容传给 LLM"""
import logging

from true_love_ai.agent.skill_registry import register_skill

LOG = logging.getLogger("FileSkill")

_MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}


def _detect_mime(file_path: str) -> str:
    suffix = "." + file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    return _MIME_MAP.get(suffix, "application/octet-stream")


@register_skill({
    "type": "function",
    "function": {
        "name": "read_file",
        "description": (
            "分析文件内容，支持 PDF、图片等格式，直接由视觉模型理解。"
            "当用户发送文件（消息中含 [文件:...] 或 [引用文件:...]）并要求分析时使用。"
            "从消息中提取文件路径（如 wx_imgs/doc.pdf）传入 file_path。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "文件路径，如 wx_imgs/document.pdf"
                },
                "question": {
                    "type": "string",
                    "description": "关于文件内容的问题或分析请求"
                }
            },
            "required": ["file_path"]
        }
    }
})
async def read_file(params: dict, ctx: dict) -> str:
    file_path = params.get("file_path", "")
    question = params.get("question", "请分析这份文件的内容")

    if not file_path:
        return "诶嘿~请提供文件路径哦~"

    mime_type = _detect_mime(file_path)
    if mime_type == "application/octet-stream":
        return f"呜呜~暂不支持该文件格式：{file_path}"

    try:
        import base64
        from true_love_ai.agent.server_client import fetch_media_bytes
        data = await fetch_media_bytes(file_path)
        if not data:
            return "呜呜~文件获取失败了捏，可能文件不存在~"

        b64 = base64.b64encode(data).decode()

        from true_love_ai.llm.router import get_llm_router
        result = await get_llm_router().vision(
            prompt=question,
            image_data=b64,
            mime_type=mime_type,
        )
        return result or "呜呜~文件分析失败了捏~"

    except Exception as e:
        LOG.error("read_file error: path=%s err=%s", file_path, e)
        return f"呜呜~文件分析出错了捏：{e}"
