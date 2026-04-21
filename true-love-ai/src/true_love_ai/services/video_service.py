#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""视频服务：文生视频 / 图生视频（OpenAI Sora 直连 / Gemini Veo 直连）"""
import asyncio
import base64
import logging
import uuid
from pathlib import Path
from typing import Optional

import litellm

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
        self.openai_key = cfg.platform_key.openai_key
        self.gemini_key = cfg.platform_key.gemini_key

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

    def _provider_of(self, model: str) -> str:
        """从模型字符串前缀判断 provider"""
        return "gemini" if model.startswith("gemini/") else "openai"

    async def _generate_by_model(
            self,
            prompt: str,
            model: str,
            img_data_list: Optional[list[str]] = None,
    ) -> VideoResponse:
        provider = self._provider_of(model)
        LOG.info("生成视频: provider=%s, model=%s", provider, model)
        if provider == "openai":
            return await self._generate_openai(prompt, model, img_data_list)
        else:
            return await self._generate_gemini(prompt, model, img_data_list)

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

    async def _generate_openai(
            self,
            prompt: str,
            model: str,
            img_data_list: Optional[list[str]] = None,
    ) -> VideoResponse:
        import tempfile, os
        if not self.openai_key:
            raise ValueError("OpenAI Key 未配置（platform_key.openai_key）")

        is_img2video = bool(img_data_list)
        LOG.info("OpenAI Sora %s: model=%s", "图生视频" if is_img2video else "文生视频", model)

        temp_file = None
        try:
            gen_params = {
                "model": model, "prompt": prompt,
                "seconds": "8", "size": "1280x720",
                "api_key": self.openai_key,
            }
            if is_img2video:
                temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                temp_file.write(base64.b64decode(img_data_list[0]))
                temp_file.close()
                gen_params["input_reference"] = open(temp_file.name, "rb")

            try:
                response = await litellm.avideo_generation(**gen_params)
            except litellm.RateLimitError:
                raise ValueError("呜呜~视频酱今天太累了，等一会再来找我玩吧~")

            video_id = response.id
            LOG.info("Sora 任务已创建: %s", video_id)

            for attempt in range(120):
                try:
                    video_bytes = await litellm.avideo_content(video_id=video_id, api_key=self.openai_key)
                    if video_bytes:
                        LOG.info("Sora 完成: %s (%.2fMB)", video_id, len(video_bytes) / 1024 / 1024)
                        break
                except litellm.RateLimitError:
                    raise ValueError("呜呜~视频酱今天太累了，等一会再来找我玩吧~")
                except Exception as e:
                    err = str(e).lower()
                    if any(k in err for k in ["rate", "quota", "429"]):
                        raise ValueError("呜呜~视频酱今天太累了，等一会再来找我玩吧~")
                    if any(k in err for k in ["content_policy", "safety", "filtered", "blocked"]):
                        raise ValueError("生成失败啦! 内容太不堪入目了吧~")
                    LOG.debug("Sora 生成中... %d/120 err=%s", attempt + 1, str(e)[:50])
                    await asyncio.sleep(5.0)
            else:
                raise ValueError("视频生成超时，请稍后再试~")

            return VideoResponse(prompt=prompt, video_base64=base64.b64encode(video_bytes).decode())
        finally:
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)

    async def _generate_gemini(
            self,
            prompt: str,
            model: str,
            img_data_list: Optional[list[str]] = None,
    ) -> VideoResponse:
        import tempfile, os
        if not self.gemini_key:
            raise ValueError("Gemini Key 未配置（platform_key.gemini_key）")

        is_img2video = bool(img_data_list)
        LOG.info("Gemini Veo %s: model=%s", "图生视频" if is_img2video else "文生视频", model)

        temp_file = None
        try:
            gen_params = {
                "model": model, "prompt": prompt,
                "size": "1280x720", "seconds": "8",
                "api_key": self.gemini_key,
            }
            if is_img2video:
                temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                temp_file.write(base64.b64decode(img_data_list[0]))
                temp_file.close()
                gen_params["input_reference"] = temp_file.name

            try:
                response = await litellm.avideo_generation(**gen_params)
            except litellm.RateLimitError:
                raise ValueError("呜呜~视频酱今天太累了，等一会再来找我玩吧~")

            video_id = response.id
            LOG.info("Veo 任务已创建: %s", video_id)
            last_status = None

            for attempt in range(120):
                try:
                    status_resp = await litellm.avideo_status(video_id=video_id, api_key=self.gemini_key)
                    status = status_resp.status
                    if status == "completed":
                        last_status = status_resp
                        break
                    if status == "failed":
                        raise ValueError("视频生成失败啦!")
                    LOG.debug("Veo 生成中... %d/120 status=%s", attempt + 1, status)
                    await asyncio.sleep(5.0)
                except litellm.RateLimitError:
                    raise ValueError("呜呜~视频酱今天太累了，等一会再来找我玩吧~")
                except ValueError:
                    raise
                except Exception as e:
                    err = str(e).lower()
                    if any(k in err for k in ["rate", "quota", "429", "resource_exhausted"]):
                        raise ValueError("呜呜~视频酱今天太累了，等一会再来找我玩吧~")
                    if any(k in err for k in ["raimediafiltered", "filtered", "safety", "policy", "blocked"]):
                        raise ValueError("生成失败啦! 内容太不堪入目了吧~")
                    raise
            else:
                raise ValueError("视频生成超时，请稍后再试~")

            try:
                video_bytes = await litellm.avideo_content(video_id=video_id, api_key=self.gemini_key)
            except Exception as e:
                err = str(e).lower()
                LOG.error("Veo 视频下载失败: %s", e)
                if "no response data" in err or "completed operation" in err:
                    raise ValueError("生成失败啦! 触发了版权过滤~")
                if any(k in err for k in ["filtered", "safety", "policy", "blocked"]):
                    raise ValueError("生成失败啦! 内容太不堪入目了吧~")
                raise ValueError("视频下载失败啦! 稍后再试试吧~")

            if not video_bytes:
                raise ValueError("生成失败啦! 触发了版权过滤~")

            vid = str(uuid.uuid4())
            video_path = GEN_VIDEO_DIR / f"{vid}.mp4"
            video_path.write_bytes(video_bytes)
            LOG.info("Veo 完成: %s (%.2fMB)", video_path, len(video_bytes) / 1024 / 1024)
            return VideoResponse(prompt=prompt, video_id=vid)

        finally:
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
