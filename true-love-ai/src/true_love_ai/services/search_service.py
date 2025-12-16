#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜索服务模块
提供百度搜索等网络搜索功能
"""
import json
import logging
import subprocess
from urllib.parse import quote_plus

LOG = logging.getLogger("SearchService")

# 百度搜索 CURL 命令模板
BAIDU_SEARCH_CURL = (
    "curl --location 'https://www.baidu.com/s?wd=%s&tn=json' "
    "--header 'User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'"
)


def fetch_baidu_references(keyword: str) -> list[dict]:
    """
    通过百度搜索获取参考信息
    
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
            text=True
        )
        
        # 解析响应
        data = json.loads(baidu_response.stdout)
        
        # 提取搜索结果
        reference_list = [
            {"content": entry['abs'], "source_url": entry['url']}
            for entry in data['feed']['entry']
            if 'abs' in entry and 'url' in entry
        ]
    except Exception:
        LOG.exception(f"百度搜索失败, keyword: {keyword}")
    
    return reference_list
