#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜索服务模块
提供百度搜索等网络搜索功能

支持 httpx 和 curl 两种实现方式
预留其他搜索后端接口
"""
import json
import logging
import subprocess
from abc import ABC, abstractmethod
from typing import Optional
from urllib.parse import quote_plus

import httpx

LOG = logging.getLogger(__name__)

# 百度搜索 CURL 命令模板
BAIDU_SEARCH_CURL = (
    "curl --location 'https://www.baidu.com/s?wd=%s&tn=json' "
    "--header 'User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'"
)


class SearchBackend(ABC):
    """搜索后端抽象基类"""

    name: str = "base"

    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        """
        执行搜索
        
        Args:
            query: 搜索关键词
            max_results: 最大结果数
            
        Returns:
            搜索结果列表，每项包含 content 和 source_url
        """
        pass


class BaiduBackend(SearchBackend):
    """
    百度搜索后端
    支持 httpx（默认）和 curl 两种方式
    """

    name = "baidu"

    def __init__(self, use_curl: bool = False):
        """
        Args:
            use_curl: 是否使用 curl 命令（默认使用 httpx）
        """
        self.use_curl = use_curl

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        """通过百度搜索获取参考信息"""
        if self.use_curl:
            return fetch_baidu_references(query)
        return await fetch_baidu_references_httpx(query)


class TavilyBackend(SearchBackend):
    """
    Tavily 搜索后端（预留）
    
    使用方式：
        backend = TavilyBackend(api_key="tvly-xxx")
        results = await backend.search("上海天气")
    """

    name = "tavily"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        # TODO: 接入 Tavily API
        # from tavily import TavilyClient
        # client = TavilyClient(api_key=self.api_key)
        # response = client.search(query, search_depth="advanced", max_results=max_results)
        # return [{"content": r["content"], "source_url": r["url"]} for r in response["results"]]
        raise NotImplementedError("Tavily backend not implemented yet")


class PerplexityBackend(SearchBackend):
    """
    Perplexity 搜索后端（预留）
    """

    name = "perplexity"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        # TODO: 接入 Perplexity API
        raise NotImplementedError("Perplexity backend not implemented yet")


def fetch_baidu_references(keyword: str) -> list[dict]:
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


class SearchService:
    """
    搜索服务
    
    支持多种搜索后端，默认使用百度
    
    使用方式：
        service = SearchService()
        results = await service.search("上海天气")
        
        # 使用其他后端
        service = SearchService(backend="tavily", api_key="xxx")
    """

    def __init__(
            self,
            backend: str = "baidu",
            api_key: Optional[str] = None
    ):
        self.backend = self._create_backend(backend, api_key)

    def _create_backend(self, name: str, api_key: Optional[str]) -> SearchBackend:
        """创建搜索后端"""
        if name == "baidu":
            return BaiduBackend()
        elif name == "tavily":
            if not api_key:
                raise ValueError("Tavily backend requires api_key")
            return TavilyBackend(api_key)
        elif name == "perplexity":
            if not api_key:
                raise ValueError("Perplexity backend requires api_key")
            return PerplexityBackend(api_key)
        else:
            raise ValueError(f"Unknown search backend: {name}")

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        """执行搜索"""
        return await self.backend.search(query, max_results)
