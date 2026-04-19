# -*- coding: utf-8 -*-
"""搜索增强 Skill（复用 AI 现有 search_service）"""
import json
import logging

from true_love_ai.agent.skill_registry import register_skill

LOG = logging.getLogger("SearchSkill")

# 百度搜索 CURL 命令模板
BAIDU_SEARCH_CURL = (
    "curl --location 'https://www.baidu.com/s?wd=%s&tn=json' "
    "--header 'User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'"
)


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
        """通过百度搜索获取参考信息"""
        if False:
            results = fetch_baidu_references(query)
        else:
            results = await fetch_baidu_references_httpx(query)
        if not results:
            return f"搜索「{query}」没有找到相关结果"
        return f"搜索「{query}」的结果：\n{json.dumps(results[:5], ensure_ascii=False, indent=2)}"
    except Exception as e:
        LOG.error("web_search error: %s", e)
        return "呜呜~搜索失败了捏，稍后再试试吧~"


def fetch_baidu_references(keyword: str) -> list[dict]:
    import json
    import subprocess
    from urllib.parse import quote_plus

    """
    通过百度搜索获取参考信息（同步方法，保持兼容）

    使用 curl 命令避免被风控

    Args:
        keyword: 搜索关键词

    Returns:
        参考信息列表，每项包含 content 和 source_url
    """
    reference_list = []
    try:
        send_curl = BAIDU_SEARCH_CURL % quote_plus(keyword)
        LOG.info(f"百度搜索: {keyword}")

        baidu_response = subprocess.run(
            send_curl,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )

        # 解析响应
        data = json.loads(baidu_response.stdout)

        # 提取搜索结果
        reference_list = [
            {"content": entry['abs'], "source_url": entry['url']}
            for entry in data['feed']['entry']
            if 'abs' in entry and 'url' in entry
        ]

        LOG.info(f"百度搜索结果数量: {len(reference_list)}")

    except subprocess.TimeoutExpired:
        LOG.error(f"百度搜索超时, keyword: {keyword}")
    except json.JSONDecodeError as e:
        LOG.error(f"百度搜索响应解析失败: {e}")
    except Exception:
        LOG.exception(f"百度搜索失败, keyword: {keyword}")

    return reference_list


async def fetch_baidu_references_httpx(keyword: str) -> list[dict]:
    import json
    import httpx
    from urllib.parse import quote_plus

    """
    通过百度搜索获取参考信息（异步方法，使用 httpx）

    Args:
        keyword: 搜索关键词

    Returns:
        参考信息列表，每项包含 content 和 source_url
    """
    reference_list = []
    url = f"https://www.baidu.com/s?wd={quote_plus(keyword)}&tn=json"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
        )
    }

    try:
        LOG.info(f"百度搜索(httpx): {keyword}")

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            # 解析响应
            data = response.json()

            # 提取搜索结果
            reference_list = [
                {"content": entry['abs'], "source_url": entry['url']}
                for entry in data['feed']['entry']
                if 'abs' in entry and 'url' in entry
            ]

            LOG.info(f"百度搜索结果数量: {len(reference_list)}")

    except httpx.TimeoutException:
        LOG.error(f"百度搜索超时(httpx), keyword: {keyword}")
    except httpx.HTTPStatusError as e:
        LOG.error(f"百度搜索HTTP错误(httpx): {e.response.status_code}")
    except json.JSONDecodeError as e:
        LOG.error(f"百度搜索响应解析失败(httpx): {e}")
    except Exception:
        LOG.exception(f"百度搜索失败(httpx), keyword: {keyword}")

    return reference_list
