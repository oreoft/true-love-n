# -*- coding: utf-8 -*-
"""搜索增强 Skill（复用 AI 现有 search_service）"""
import json
import logging

from true_love_ai.agent.skill_registry import register_skill

LOG = logging.getLogger("SearchSkill")


@register_skill({
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "联网搜索实时信息，适合查询新闻、实时数据、近期事件等。"
            "当用户需要搜索最新资讯、当前股价、天气预报等实时信息时使用。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "完整、具体的搜索关键词（中文）"
                }
            },
            "required": ["query"]
        }
    }
})
async def web_search(params: dict, ctx: dict) -> str:
    query = params.get("query", "")
    if not query:
        return "诶嘿~请提供搜索关键词哦~"

    try:
        from true_love_ai.services.search_service import SearchService
        service = SearchService('baidu', None)
        results = await service.search(query)
        if not results:
            return f"搜索「{query}」没有找到相关结果"
        return f"搜索「{query}」的结果：\n{json.dumps(results[:5], ensure_ascii=False, indent=2)}"
    except Exception as e:
        LOG.error("web_search error: %s", e)
        return "呜呜~搜索失败了捏，稍后再试试吧~"
