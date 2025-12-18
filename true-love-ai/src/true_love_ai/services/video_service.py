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
from typing import Optional

import httpx

from true_love_ai.core.config import get_config
from true_love_ai.core.session import get_session_manager
from true_love_ai.llm.router import get_llm_router
from true_love_ai.models.response import VideoResponse

LOG = logging.getLogger(__name__)

# 视频生成支持的 provider
VIDEO_PROVIDERS = ["openai", "gemini"]


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
        """
        # 获取 API Key
        api_key = None
        if self.config.chatgpt:
            api_key = self.config.chatgpt.key1 or self.config.chatgpt.key2 or self.config.chatgpt.key3
        
        if not api_key:
            raise ValueError("OpenAI API Key 未配置，无法生成视频呢~")
        
        model_name = self.config.chatgpt.openai_video_model if self.config.chatgpt else "sora"
        LOG.info(f"OpenAI Sora 生成视频, model: {model_name}, prompt: {prompt[:50]}...")
        
        async with httpx.AsyncClient() as client:
            # 创建视频生成任务
            response = await client.post(
                "https://api.openai.com/v1/videos/generations",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "size": "1080x1920",  # 竖屏
                    "duration": 5
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
            
            # 轮询获取结果
            video_url = await self._poll_openai_video(client, api_key, video_id)
            
            return VideoResponse(
                prompt=prompt,
                video_url=video_url
            )
    
    async def _generate_openai_from_images(
        self,
        prompt: str,
        img_data_list: list[str]
    ) -> VideoResponse:
        """
        使用 OpenAI Sora 图生视频
        """
        # 获取 API Key
        api_key = None
        if self.config.chatgpt:
            api_key = self.config.chatgpt.key1 or self.config.chatgpt.key2 or self.config.chatgpt.key3
        
        if not api_key:
            raise ValueError("OpenAI API Key 未配置，无法生成视频呢~")
        
        model_name = self.config.chatgpt.openai_video_model if self.config.chatgpt else "sora"
        LOG.info(f"OpenAI Sora 图生视频, model: {model_name}, 图片数量: {len(img_data_list)}")
        
        # 构建图片输入
        image_inputs = []
        for img_data in img_data_list:
            image_inputs.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{img_data}"
                }
            })
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/videos/generations",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "image": image_inputs[0]["image_url"] if len(image_inputs) == 1 else None,
                    "size": "1080x1920",
                    "duration": 5
                },
                timeout=60.0
            )
            
            if response.status_code not in [200, 201]:
                error_msg = response.text
                LOG.error(f"OpenAI 图生视频请求失败: {response.status_code}, {error_msg}")
                raise ValueError("图生视频请求失败啦!")
            
            data = response.json()
            video_id = data.get("id")
            
            if not video_id:
                raise ValueError("图生视频请求失败啦!")
            
            # 轮询获取结果
            video_url = await self._poll_openai_video(client, api_key, video_id)
            
            return VideoResponse(
                prompt=prompt,
                video_url=video_url
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
                        "aspectRatio": "9:16",  # 竖屏
                        "durationSeconds": 5
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
            
            # 轮询获取结果
            video_data = await self._poll_gemini_video(client, api_key, operation_name)
            
            return VideoResponse(
                prompt=prompt,
                video_url=video_data.get("url", ""),
                video_base64=video_data.get("base64", "")
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
                        "aspectRatio": "9:16",
                        "durationSeconds": 5
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
            
            # 轮询获取结果
            video_data = await self._poll_gemini_video(client, api_key, operation_name)
            
            return VideoResponse(
                prompt=prompt,
                video_url=video_data.get("url", ""),
                video_base64=video_data.get("base64", "")
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
        轮询 Gemini 视频生成结果
        
        Args:
            client: HTTP 客户端
            api_key: API Key
            operation_name: 操作名称
            max_attempts: 最大尝试次数
            interval: 轮询间隔（秒）
            
        Returns:
            {"url": str, "base64": str}
        """
        LOG.info(f"开始轮询 Gemini 视频生成结果, operation: {operation_name}")
        
        for attempt in range(max_attempts):
            response = await client.get(
                f"https://generativelanguage.googleapis.com/v1beta/{operation_name}",
                params={"key": api_key},
                timeout=30.0
            )
            
            if response.status_code != 200:
                LOG.warning(f"轮询失败: {response.status_code}")
                await asyncio.sleep(interval)
                continue
            
            data = response.json()
            done = data.get("done", False)
            
            if done:
                # 检查是否有错误
                if "error" in data:
                    error = data["error"]
                    LOG.error(f"视频生成失败: {error}")
                    raise ValueError(f"视频生成失败: {error.get('message', '未知错误')}")
                
                # 获取结果
                result = data.get("response", {})
                predictions = result.get("predictions", [])
                
                if predictions and len(predictions) > 0:
                    video_data = predictions[0]
                    video_url = video_data.get("videoUri", "")
                    video_base64 = video_data.get("bytesBase64Encoded", "")
                    
                    if video_url or video_base64:
                        LOG.info(f"视频生成完成")
                        return {"url": video_url, "base64": video_base64}
                
                LOG.error(f"视频生成完成但数据异常: {data}")
                raise ValueError("视频生成完成但未返回视频数据")
            
            # 获取进度信息
            metadata = data.get("metadata", {})
            progress = metadata.get("progress", 0)
            LOG.debug(f"视频生成中... 进度: {progress}%, 尝试: {attempt + 1}/{max_attempts}")
            
            await asyncio.sleep(interval)
        
        raise ValueError("视频生成超时，请稍后再试~")
