#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""图像服务：文生图（Gemini / OpenAI）+ 图像分析"""
import base64
import logging
from pathlib import Path
from typing import Optional

GEN_IMG_DIR = Path("gen_img")
GEN_IMG_DIR.mkdir(exist_ok=True)

import httpx
import litellm

from true_love_ai.core.config import get_config
from true_love_ai.llm.router import get_llm_router
from true_love_ai.models.response import ImageResponse

LOG = logging.getLogger(__name__)


class ImageService:

    def __init__(self):
        self.config = get_config()
        self.llm_router = get_llm_router()
        self.litellm_api_key = self.config.platform_key.litellm_api_key
        self.litellm_base_url = self.config.platform_key.litellm_base_url

    async def generate_image(
            self,
            image_prompt: str,
            provider: Optional[str] = None,
    ) -> ImageResponse:
        """
        文生图。
        provider=None  → 优先 Gemini，失败自动降级 OpenAI
        provider=gemini/openai → 强制使用，失败直接抛出
        """

        if provider == "openai":
            return await self._generate_openai(image_prompt)
        if provider == "gemini":
            return await self._generate_gemini(image_prompt)

        # 默认：Gemini 优先，降级 OpenAI
        try:
            return await self._generate_gemini(image_prompt)
        except Exception as e:
            LOG.warning("Gemini 生图失败，降级到 OpenAI: %s", e)
            return await self._generate_openai(image_prompt)

    async def _generate_openai(self, prompt: str) -> ImageResponse:
        api_key = None
        if self.config.chatgpt:
            api_key = self.config.chatgpt.key1 or self.config.chatgpt.key2 or self.config.chatgpt.key3
        if not api_key:
            raise ValueError("OpenAI API Key 未配置")

        image_model = self.config.chatgpt.image_model if self.config.chatgpt else "gpt-image-1"
        LOG.info("OpenAI 生图: model=%s, prompt=%s...", image_model, prompt[:50])

        try:
            response = await litellm.aimage_generation(
                model=image_model,
                prompt=prompt,
                n=1,
                api_key=self.litellm_api_key,
                api_base=self.litellm_base_url,
                response_format="b64_json",
            )
            if response.data and response.data[0].b64_json:
                return ImageResponse(prompt=prompt, img=response.data[0].b64_json)
            raise ValueError("返回数据异常")
        except litellm.exceptions.ContentPolicyViolationError:
            raise ValueError("生成失败啦! 内容太不堪入目了吧~")
        except litellm.exceptions.Timeout:
            raise ValueError("生成超时啦! 稍后再试试吧~")
        except ValueError:
            raise
        except Exception as e:
            LOG.error("OpenAI 生图异常: %s", e)
            raise ValueError("生成失败啦!")

    async def _generate_gemini(self, prompt: str) -> ImageResponse:
        api_key = self.config.chatgpt.gemini_key1 if self.config.chatgpt else None
        if not api_key:
            raise ValueError("Gemini API Key 未配置")

        litellm_model = self.config.chatgpt.gemini_image_model if self.config.chatgpt else "imagen-4.0-generate-001"
        LOG.info("Gemini 生图: model=%s, prompt=%s...", litellm_model, prompt[:50])

        try:
            response = await litellm.aimage_generation(
                model=litellm_model,
                prompt=prompt,
                api_key=self.litellm_api_key,
                api_base=self.litellm_base_url,
                response_format="b64_json",
                n=1,
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
        except ValueError:
            raise
        except Exception as e:
            LOG.error("Gemini 生图异常: %s", e)
            raise ValueError("生成失败啦!")

    async def analyze_image(
            self,
            content: str,
            img_data: str,
            provider: Optional[str] = None,
            model: Optional[str] = None,
    ) -> str:
        """图像分析"""
        LOG.info("分析图像: %s...", content[:50])
        is_debug = content.startswith("debug")
        clean_content = content.removeprefix("debug").strip() if is_debug else content

        analyze_prompt = self.config.chatgpt.prompt6 if self.config.chatgpt else "请分析这张图片"
        result = await self.llm_router.vision(
            prompt=f"{analyze_prompt}\n\n用户问题: {clean_content}",
            image_data=img_data,
            provider=provider,
            model=model,
        )

        if is_debug:
            result = f"{result}\n\n(provider: {provider or 'default'}, model: {model or 'default'})"
        return result
