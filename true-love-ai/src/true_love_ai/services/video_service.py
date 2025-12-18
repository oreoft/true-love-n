#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频服务模块
提供视频生成功能：文生视频、图生视频
支持 OpenAI (Sora) 和 Gemini (Veo)
"""
import asyncio
import base64
import logging
import random
import uuid
from pathlib import Path
from typing import Optional

import httpx

from true_love_ai.core.config import get_config
from true_love_ai.core.session import get_session_manager
from true_love_ai.llm.router import get_llm_router
from true_love_ai.models.response import VideoResponse

LOG = logging.getLogger(__name__)

# 视频生成支持的 provider
VIDEO_PROVIDERS = ["openai", "gemini"]

# Gemini 视频存储目录
GEN_VIDEO_DIR = Path("gen_video")
GEN_VIDEO_DIR.mkdir(exist_ok=True)


class VideoService:
    """
    视频服务
    支持多种视频提供商：OpenAI (Sora)、Gemini (Veo)
    """

    def __init__(self):
        self.config = get_config()
        self.llm_router = get_llm_router()
        self.session_manager = get_session_manager()

    async def generate_video(
            self,
            content: str,
            img_data_list: Optional[list[str]] = None,
            wxid: str = "",
            sender: str = "",
            provider: Optional[str] = None,
            model: Optional[str] = None
    ) -> VideoResponse:
        """
        生成视频
        
        Args:
            content: 视频描述
            img_data_list: base64 图像列表（图生视频时使用）
            wxid: 会话 ID
            sender: 发送者
            provider: 提供商 (openai/gemini)
            model: 模型
            
        Returns:
            VideoResponse
        """
        if img_data_list and len(img_data_list) > 0:
            # 图生视频
            return await self._generate_from_images(
                content=content,
                img_data_list=img_data_list,
                wxid=wxid,
                provider=provider,
                model=model
            )
        else:
            # 文生视频
            return await self._generate_from_text(
                content=content,
                wxid=wxid,
                provider=provider,
                model=model
            )

    async def _generate_from_text(
            self,
            content: str,
            wxid: str = "",
            provider: Optional[str] = None,
            model: Optional[str] = None
    ) -> VideoResponse:
        """
        文生视频
        
        Args:
            content: 用户描述
            wxid: 会话 ID
            provider: 提供商
            model: 模型
        """
        LOG.info(f"开始文生视频: {content[:50]}...")

        # 先生成视频描述词
        video_prompt_config = self.config.chatgpt.prompt4 if self.config.chatgpt else ""

        try:
            video_prompt = await self.llm_router.chat(
                messages=[
                    {"role": "system", "content": video_prompt_config},
                    {"role": "user", "content": f"请为以下视频描述生成适合AI视频生成的英文prompt：{content}"}
                ],
                provider=provider,
                model=model
            )
            LOG.info(f"生成的视频描述词: {video_prompt[:100]}...")
        except Exception as e:
            LOG.warning(f"生成描述词失败，使用原始内容: {e}")
            video_prompt = content

        # 保存到会话历史
        if wxid:
            session = self.session_manager.get_or_create(wxid)
            session.add_message("user", content)
            session.add_message("assistant", f"[生成视频] {video_prompt}")

        # 根据 provider 选择生成服务（未指定时随机选择）
        provider = provider or random.choice(VIDEO_PROVIDERS)
        LOG.info(f"使用 {provider} 生成视频")

        if provider.lower() == "openai":
            return await self._generate_openai(video_prompt)
        else:
            return await self._generate_gemini(video_prompt)

    async def _generate_from_images(
            self,
            content: str,
            img_data_list: list[str],
            wxid: str = "",
            provider: Optional[str] = None,
            model: Optional[str] = None
    ) -> VideoResponse:
        """
        图生视频
        
        Args:
            content: 视频描述
            img_data_list: base64 图像列表
            wxid: 会话 ID
            provider: 提供商
            model: 模型
        """
        LOG.info(f"开始图生视频: {content[:50]}..., 图片数量: {len(img_data_list)}")

        # 保存到会话历史
        if wxid:
            session = self.session_manager.get_or_create(wxid)
            session.add_message("user", f"[图生视频] {content}")
            session.add_message("assistant", f"[生成视频中] 使用 {len(img_data_list)} 张图片")

        # 根据 provider 选择生成服务（未指定时随机选择）
        provider = provider or random.choice(VIDEO_PROVIDERS)
        LOG.info(f"使用 {provider} 图生视频")

        if provider.lower() == "openai":
            return await self._generate_openai_from_images(content, img_data_list)
        else:
            return await self._generate_gemini_from_images(content, img_data_list)

    # ==================== OpenAI Sora ====================

    async def _generate_openai(self, prompt: str) -> VideoResponse:
        """
        使用 OpenAI Sora 生成视频（文生视频）
        API 文档: https://platform.openai.com/docs/guides/video-generation
        """
        # 获取 API Key
        api_key = None
        if self.config.chatgpt:
            api_key = self.config.chatgpt.key1 or self.config.chatgpt.key2 or self.config.chatgpt.key3

        if not api_key:
            raise ValueError("OpenAI API Key 未配置，无法生成视频呢~")

        # 获取配置
        model_name = self.config.chatgpt.openai_video_model if self.config.chatgpt else "sora-2"
        api_base = self.config.chatgpt.api if self.config.chatgpt else "https://api.openai.com/v1/"
        api_base = api_base.rstrip("/")

        LOG.info(f"OpenAI Sora 生成视频, model: {model_name}, prompt: {prompt[:50]}...")

        async with httpx.AsyncClient() as client:
            # 创建视频生成任务 - 端点是 /v1/videos
            response = await client.post(
                f"{api_base}/videos",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "seconds": "12"  # 字符串，只能是 "4", "8", "12"
                },
                timeout=60.0
            )

            if response.status_code not in [200, 201]:
                error_msg = response.text
                LOG.error(f"OpenAI 视频生成请求失败: {response.status_code}, {error_msg}")
                raise ValueError("视频生成请求失败啦! 可能是服务暂时不可用~")

            data = response.json()
            video_id = data.get("id")

            if not video_id:
                LOG.error(f"OpenAI 返回数据异常: {data}")
                raise ValueError("视频生成请求失败啦!")

            LOG.info(f"视频任务已创建, video_id: {video_id}")

            # 轮询获取结果
            video_base64 = await self._poll_openai_video(client, api_key, video_id, api_base)

            return VideoResponse(
                prompt=prompt,
                video_base64=video_base64
            )

    async def _generate_openai_from_images(
            self,
            prompt: str,
            img_data_list: list[str]
    ) -> VideoResponse:
        """
        使用 OpenAI Sora 图生视频
        使用 input_reference 参数传入参考图片
        """
        # 获取 API Key
        api_key = None
        if self.config.chatgpt:
            api_key = self.config.chatgpt.key1 or self.config.chatgpt.key2 or self.config.chatgpt.key3

        if not api_key:
            raise ValueError("OpenAI API Key 未配置，无法生成视频呢~")

        # 获取配置
        model_name = self.config.chatgpt.openai_video_model if self.config.chatgpt else "sora-2"
        api_base = self.config.chatgpt.api if self.config.chatgpt else "https://api.openai.com/v1/"
        api_base = api_base.rstrip("/")

        LOG.info(f"OpenAI Sora 图生视频, model: {model_name}, 图片数量: {len(img_data_list)}")

        # 使用第一张图片作为参考
        first_image = img_data_list[0]

        async with httpx.AsyncClient() as client:
            # 使用 multipart/form-data 上传图片
            files = {
                "input_reference": ("image.jpg", base64.b64decode(first_image), "image/jpeg")
            }
            data = {
                "model": model_name,
                "prompt": prompt,
                "seconds": '12'
            }

            response = await client.post(
                f"{api_base}/videos",
                headers={
                    "Authorization": f"Bearer {api_key}"
                },
                files=files,
                data=data,
                timeout=60.0
            )

            if response.status_code not in [200, 201]:
                error_msg = response.text
                LOG.error(f"OpenAI 图生视频请求失败: {response.status_code}, {error_msg}")
                raise ValueError("图生视频请求失败啦!")

            resp_data = response.json()
            video_id = resp_data.get("id")

            if not video_id:
                raise ValueError("图生视频请求失败啦!")

            LOG.info(f"图生视频任务已创建, video_id: {video_id}")

            # 轮询获取结果
            video_base64 = await self._poll_openai_video(client, api_key, video_id, api_base)

            return VideoResponse(
                prompt=prompt,
                video_base64=video_base64
            )

    async def _poll_openai_video(
            self,
            client: httpx.AsyncClient,
            api_key: str,
            video_id: str,
            max_attempts: int = 120,
            interval: float = 5.0
    ) -> str:
        """
        轮询 OpenAI 视频生成结果
        
        Args:
            client: HTTP 客户端
            api_key: API Key
            video_id: 视频任务 ID
            max_attempts: 最大尝试次数
            interval: 轮询间隔（秒）
            
        Returns:
            视频 URL
        """
        LOG.info(f"开始轮询 OpenAI 视频生成结果, video_id: {video_id}")

        for attempt in range(max_attempts):
            response = await client.get(
                f"https://api.openai.com/v1/videos/generations/{video_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30.0
            )

            if response.status_code != 200:
                LOG.warning(f"轮询失败: {response.status_code}")
                await asyncio.sleep(interval)
                continue

            data = response.json()
            status = data.get("status")

            if status == "completed":
                video_url = data.get("video", {}).get("url") or data.get("url")
                if video_url:
                    LOG.info(f"视频生成完成: {video_url[:50]}...")
                    return video_url
                raise ValueError("视频生成完成但未返回URL")

            elif status == "failed":
                error = data.get("error", "未知错误")
                LOG.error(f"视频生成失败: {error}")
                raise ValueError(f"视频生成失败: {error}")

            LOG.debug(f"视频生成中... 状态: {status}, 尝试: {attempt + 1}/{max_attempts}")
            await asyncio.sleep(interval)

        raise ValueError("视频生成超时，请稍后再试~")

    # ==================== Gemini Veo ====================

    async def _generate_gemini(self, prompt: str) -> VideoResponse:
        """
        使用 Gemini Veo 生成视频（文生视频）
        """
        # 获取 API Key
        api_key = None
        if self.config.chatgpt:
            api_key = self.config.chatgpt.gemini_key1

        if not api_key:
            raise ValueError("Gemini API Key 未配置，无法生成视频呢~")

        model_name = self.config.chatgpt.gemini_video_model if self.config.chatgpt else "veo-2.0-generate-001"
        LOG.info(f"Gemini Veo 生成视频, model: {model_name}, prompt: {prompt[:50]}...")

        async with httpx.AsyncClient() as client:
            # 创建视频生成任务
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:predictLongRunning",
                params={"key": api_key},
                headers={"Content-Type": "application/json"},
                json={
                    "instances": [
                        {"prompt": prompt}
                    ],
                    "parameters": {
                        "aspectRatio": "16:9",
                        "durationSeconds": 8  # Veo 3.1 支持 4, 6, 8（整数）
                    }
                },
                timeout=60.0
            )

            if response.status_code != 200:
                error_msg = response.text
                LOG.error(f"Gemini 视频生成请求失败: {response.status_code}, {error_msg}")
                raise ValueError("视频生成请求失败啦!")

            data = response.json()
            operation_name = data.get("name")

            if not operation_name:
                LOG.error(f"Gemini 返回数据异常: {data}")
                raise ValueError("视频生成请求失败啦!")

            # 轮询获取结果并下载视频
            video_data = await self._poll_gemini_video(client, api_key, operation_name)

            return VideoResponse(
                prompt=prompt,
                video_id=video_data.get("video_id")
            )

    async def _generate_gemini_from_images(
            self,
            prompt: str,
            img_data_list: list[str]
    ) -> VideoResponse:
        """
        使用 Gemini Veo 图生视频
        """
        # 获取 API Key
        api_key = None
        if self.config.chatgpt:
            api_key = self.config.chatgpt.gemini_key1

        if not api_key:
            raise ValueError("Gemini API Key 未配置，无法生成视频呢~")

        model_name = self.config.chatgpt.gemini_video_model if self.config.chatgpt else "veo-2.0-generate-001"
        LOG.info(f"Gemini Veo 图生视频, model: {model_name}, 图片数量: {len(img_data_list)}")

        # 构建图片输入
        image_inputs = []
        for img_data in img_data_list:
            image_inputs.append({
                "bytesBase64Encoded": img_data,
                "mimeType": "image/jpeg"
            })

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:predictLongRunning",
                params={"key": api_key},
                headers={"Content-Type": "application/json"},
                json={
                    "instances": [
                        {
                            "prompt": prompt,
                            "image": image_inputs[0] if len(image_inputs) == 1 else None,
                            "referenceImages": image_inputs if len(image_inputs) > 1 else None
                        }
                    ],
                    "parameters": {
                        "aspectRatio": "16:9",
                        "durationSeconds": 8  # Veo 3.1 支持 4, 6, 8（整数）
                    }
                },
                timeout=60.0
            )

            if response.status_code != 200:
                error_msg = response.text
                LOG.error(f"Gemini 图生视频请求失败: {response.status_code}, {error_msg}")
                raise ValueError("图生视频请求失败啦!")

            data = response.json()
            operation_name = data.get("name")

            if not operation_name:
                raise ValueError("图生视频请求失败啦!")

            # 轮询获取结果并下载视频
            video_data = await self._poll_gemini_video(client, api_key, operation_name)

            return VideoResponse(
                prompt=prompt,
                video_id=video_data.get("video_id")
            )

    async def _poll_gemini_video(
            self,
            client: httpx.AsyncClient,
            api_key: str,
            operation_name: str,
            max_attempts: int = 120,
            interval: float = 5.0
    ) -> dict:
        """
        轮询 Gemini 视频生成结果，下载视频到本地
        
        Args:
            client: HTTP 客户端
            api_key: API Key
            operation_name: 操作名称
            max_attempts: 最大尝试次数
            interval: 轮询间隔（秒）
            
        Returns:
            {"video_id": str} - 本地视频文件 ID
        """
        LOG.info(f"开始轮询 Gemini 视频生成结果, operation: {operation_name}")

        for attempt in range(max_attempts):
            response = await client.get(
                f"https://generativelanguage.googleapis.com/v1beta/{operation_name}",
                params={"key": api_key},
                timeout=30.0
            )

            if response.status_code != 200:
                LOG.warning(f"{operation_name}-轮询失败: {response.status_code}")
                await asyncio.sleep(interval)
                continue

            data = response.json()
            done = data.get("done", False)

            if done:
                # 检查是否有错误
                if "error" in data:
                    error = data["error"]
                    LOG.error(f"{operation_name}-视频生成失败: {error}")
                    raise ValueError(f"{operation_name}-视频生成失败: {error.get('message', '未知错误')}")

                # 获取结果 - 支持两种返回格式
                result = data.get("response", {})
                video_url = None
                video_base64 = None
                
                # 新格式: generateVideoResponse.generatedSamples[0].video.uri
                gen_response = result.get("generateVideoResponse", {})
                samples = gen_response.get("generatedSamples", [])
                if samples:
                    video_info = samples[0].get("video", {})
                    video_url = video_info.get("uri", "")
                
                # 旧格式: predictions[0].videoUri
                if not video_url:
                    predictions = result.get("predictions", [])
                    if predictions:
                        video_data = predictions[0]
                        video_url = video_data.get("videoUri", "")
                        video_base64 = video_data.get("bytesBase64Encoded", "")
                
                # 下载视频到本地
                if video_url:
                    LOG.info(f"{operation_name}-视频生成完成, 开始下载...")
                    video_id = await self._download_gemini_video(client, api_key, video_url)
                    return {"video_id": video_id}
                elif video_base64:
                    # 如果返回的是 base64，直接保存
                    video_id = str(uuid.uuid4())
                    video_path = GEN_VIDEO_DIR / f"{video_id}.mp4"
                    video_path.write_bytes(base64.b64decode(video_base64))
                    LOG.info(f"{operation_name}-视频已保存: {video_path}")
                    return {"video_id": video_id}

                LOG.error(f"{operation_name}-视频生成完成但数据异常: {data}")
                raise ValueError(f"{operation_name}-视频生成完成但未返回视频数据")

            # 获取进度信息
            metadata = data.get("metadata", {})
            progress = metadata.get("progress", 0)
            LOG.debug(f"{operation_name}-视频生成中... 进度: {progress}%, 尝试: {attempt + 1}/{max_attempts}")

            await asyncio.sleep(interval)

        raise ValueError(f"{operation_name}-视频生成超时，请稍后再试~")

    async def _download_gemini_video(
            self,
            client: httpx.AsyncClient,
            api_key: str,
            video_url: str
    ) -> str:
        """
        下载 Gemini 视频到本地
        
        Args:
            client: HTTP 客户端
            api_key: API Key
            video_url: 视频 URL
            
        Returns:
            video_id: 视频文件 ID
        """
        video_id = str(uuid.uuid4())
        video_path = GEN_VIDEO_DIR / f"{video_id}.mp4"
        
        # 使用 API key 下载视频
        response = await client.get(
            video_url,
            headers={"x-goog-api-key": api_key},
            follow_redirects=True,
            timeout=120.0
        )
        
        if response.status_code != 200:
            LOG.error(f"下载视频失败: {response.status_code}, {response.text[:200]}")
            raise ValueError("下载视频失败")
        
        video_path.write_bytes(response.content)
        LOG.info(f"视频已下载: {video_path}, 大小: {len(response.content) / 1024 / 1024:.2f}MB")
        
        return video_id
