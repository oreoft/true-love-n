#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""视频服务：文生视频 / 图生视频（通过 LiteLLM proxy HTTP API）"""
import asyncio
import base64
import logging
import uuid
from pathlib import Path
from typing import Optional

import httpx

from true_love_ai.core.config import get_config
from true_love_ai.core.model_registry import get_model_registry
from true_love_ai.llm.router import get_llm_router
from true_love_ai.models.response import VideoResponse

LOG = logging.getLogger(__name__)

GEN_VIDEO_DIR = Path("gen_video")
GEN_VIDEO_DIR.mkdir(exist_ok=True)

_VIDEO_PROMPT_SYSTEM = (
    "把用户的视频描述翻译并优化为适合 AI 生视频的英文 prompt，直接输出英文，不超过 150 词，不要解释。"
)


class VideoService:

    def __init__(self):
        cfg = get_config()
        self.llm_router = get_llm_router()
        self.registry = get_model_registry()
        self.base_url = cfg.platform_key.litellm_base_url.rstrip("/")
        self.api_key = cfg.platform_key.litellm_api_key

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def generate_video(
            self,
            content: str,
            img_data_list: Optional[list[str]] = None,
    ) -> VideoResponse:
        video_prompt = await self._build_prompt(content)
        default_model  = self.registry.get("video", "default")
        fallback_model = self.registry.get("video", "fallback")

        try:
            return await self._generate_by_model(video_prompt, default_model, img_data_list)
        except Exception as e:
            if fallback_model:
                LOG.warning("主力视频生成失败，降级备用模型 %s: %s", fallback_model, e)
                return await self._generate_by_model(video_prompt, fallback_model, img_data_list)
            raise

    async def _build_prompt(self, content: str) -> str:
        try:
            return await self.llm_router.chat(
                messages=[
                    {"role": "system", "content": _VIDEO_PROMPT_SYSTEM},
                    {"role": "user", "content": content},
                ]
            )
        except Exception as e:
            LOG.warning("视频 prompt 翻译失败，使用原始内容: %s", e)
            return content

    async def _generate_by_model(
            self,
            prompt: str,
            model: str,
            img_data_list: Optional[list[str]] = None,
    ) -> VideoResponse:
        is_img2video = bool(img_data_list)
        LOG.info("生成视频: model=%s %s", model, "图生视频" if is_img2video else "文生视频")

        body: dict = {"model": model, "prompt": prompt, "size": "1280x720", "seconds": "8"}
        if is_img2video:
            body["input_reference"] = img_data_list[0]

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/v1/videos",
                headers=self._headers(),
                json=body,
            )
            self._raise_for_video_error(resp)
            data = resp.json()

        video_id = data.get("id")
        if not video_id:
            raise ValueError("视频任务创建失败：未获取到 job id")
        LOG.info("视频任务已创建: %s", video_id)

        video_bytes = await self._poll_and_download(video_id)
        vid = str(uuid.uuid4())
        video_path = GEN_VIDEO_DIR / f"{vid}.mp4"
        video_path.write_bytes(video_bytes)
        LOG.info("视频完成: %s (%.2fMB)", video_path, len(video_bytes) / 1024 / 1024)
        return VideoResponse(prompt=prompt, video_id=vid)

    async def _poll_and_download(self, video_id: str) -> bytes:
        for attempt in range(120):
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self.base_url}/v1/videos/{video_id}",
                    headers=self._headers(),
                )
                self._raise_for_video_error(resp)
                data = resp.json()

            status = data.get("status", "")
            if status == "completed":
                break
            if status == "failed":
                raise ValueError("视频生成失败啦!")
            LOG.debug("视频生成中... %d/120 status=%s", attempt + 1, status)
            await asyncio.sleep(5.0)
        else:
            raise ValueError("视频生成超时，请稍后再试~")

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.get(
                f"{self.base_url}/v1/videos/{video_id}/content",
                headers=self._headers(),
            )
            self._raise_for_video_error(resp)
            return resp.content

    @staticmethod
    def _raise_for_video_error(resp: httpx.Response) -> None:
        if resp.status_code == 429:
            raise ValueError("呜呜~视频酱今天太累了，等一会再来找我玩吧~")
        if resp.status_code >= 400:
            err = resp.text.lower()
            if any(k in err for k in ["content_policy", "safety", "filtered", "blocked"]):
                raise ValueError("生成失败啦! 内容太不堪入目了吧~")
            raise ValueError(f"视频接口错误 {resp.status_code}: {resp.text[:200]}")
