#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""图像服务：文生图（LiteLLM 统一入口）+ 图像分析"""
import base64
import logging
from pathlib import Path
from typing import Optional

import httpx
import litellm

from true_love_ai.core.config import get_config
from true_love_ai.core.model_registry import get_model_registry
from true_love_ai.llm.router import get_llm_router
from true_love_ai.models.response import ImageResponse

GEN_IMG_DIR = Path("gen_img")
GEN_IMG_DIR.mkdir(exist_ok=True)

LOG = logging.getLogger(__name__)


class ImageService:

    def __init__(self):
        cfg = get_config()
        self.llm = cfg.llm
        self.llm_router = get_llm_router()
        self.registry = get_model_registry()
        self.litellm_api_key = cfg.platform_key.litellm_api_key
        self.litellm_base_url = cfg.platform_key.litellm_base_url

    async def generate_image(
            self,
            image_prompt: str,
            provider: Optional[str] = None,
    ) -> ImageResponse:
        """
        文生图。
        provider=None  → 用 default，失败自动降级 fallback
        provider=openai/gemini → 强制使用匹配的模型
        """
        default_model  = self.registry.get("image", "default")
        fallback_model = self.registry.get("image", "fallback")

        if provider:
            model = default_model if provider in default_model else fallback_model
            return await self._generate(image_prompt, model)

        # 自动：default 优先，失败降级 fallback
        try:
            return await self._generate(image_prompt, default_model)
        except Exception as e:
            if fallback_model:
                LOG.warning("主力生图失败，降级备用模型 %s: %s", fallback_model, e)
                return await self._generate(image_prompt, fallback_model)
            raise

    async def _generate(self, prompt: str, model: str) -> ImageResponse:
        LOG.info("生图: model=%s, prompt=%s...", model, prompt[:50])
        try:
            response = await litellm.aimage_generation(
                model=model, prompt=prompt, n=1,
                api_key=self.litellm_api_key, api_base=self.litellm_base_url,
                response_format="b64_json",
            )
            if response.data:
                item = response.data[0]
                if getattr(item, "b64_json", None):
                    return ImageResponse(prompt=prompt, img=item.b64_json)
                if getattr(item, "url", None):
                    async with httpx.AsyncClient() as client:
                        r = await client.get(item.url, timeout=60.0)
                        if r.status_code == 200:
                            return ImageResponse(prompt=prompt, img=base64.b64encode(r.content).decode())
            raise ValueError("返回数据异常")
        except litellm.exceptions.ContentPolicyViolationError:
            raise ValueError("生成失败啦! 内容太不堪入目了吧~")
        except litellm.exceptions.Timeout:
            raise ValueError("生成超时啦! 稍后再试试吧~")
        except ValueError:
            raise
        except Exception as e:
            LOG.error("生图异常 model=%s: %s", model, e)
            raise ValueError("生成失败啦!")

    async def analyze_image(
            self,
            content: str,
            img_data: str,
            model: Optional[str] = None,
    ) -> str:
        LOG.info("分析图像: %s...", content[:50])
        is_debug = content.startswith("debug")
        clean_content = content.removeprefix("debug").strip() if is_debug else content

        analyze_prompt = self.llm.vision_prompt if self.llm else "请分析这张图片"
        result = await self.llm_router.vision(
            prompt=f"{analyze_prompt}\n\n用户问题: {clean_content}",
            image_data=img_data,
            model=model,
        )

        if is_debug:
            result = f"{result}\n\n(model: {model or 'default'})"
        return result
