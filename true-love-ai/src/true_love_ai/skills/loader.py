#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Schema Loader

AI 服务启动时从 Server 拉取所有 skill tool schemas，
缓存在内存中供意图识别使用。
"""
import logging
from typing import Optional

import httpx

LOG = logging.getLogger(__name__)

# 内存缓存
_skill_schemas: list[dict] = []


async def load_skill_schemas(server_host: str, timeout: float = 5.0, retries: int = 3) -> list[dict]:
    """
    从 Server 的 /api/internal/skills 拉取 skill tool schemas。

    Args:
        server_host: Server 地址，如 http://true-love-server:8080
        timeout:     单次请求超时（秒）
        retries:     失败重试次数

    Returns:
        skill tool schemas 列表，失败时返回空列表（降级）
    """
    global _skill_schemas
    url = f"{server_host}/api/internal/skills"

    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                schemas = data.get("data", [])
                if isinstance(schemas, list):
                    _skill_schemas = schemas
                    LOG.info("成功加载 %d 个 skill schemas from %s", len(schemas), url)
                    return schemas
        except Exception as e:
            LOG.warning("skill schema 加载失败 (第%d/%d次): %s", attempt, retries, e)
            if attempt < retries:
                import asyncio
                await asyncio.sleep(2)

    LOG.warning("skill schemas 加载全部失败，降级为空列表（无 skill 能力）")
    _skill_schemas = []
    return []


def get_skill_schemas() -> list[dict]:
    """获取已缓存的 skill schemas（同步，供意图识别使用）"""
    return _skill_schemas


def is_skill_loaded() -> bool:
    """是否已成功加载 skill schemas"""
    return len(_skill_schemas) > 0
