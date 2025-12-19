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

from true_love_ai.core.config import get_config
from true_love_ai.core.session import get_session_manager
from true_love_ai.llm.router import get_llm_router
from true_love_ai.llm import video_prompt
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

        # 使用新的提示词系统生成视频描述词
        video_prompt_text = await self._generate_video_prompt(
            content=content,
            provider=provider,
            model=model
        )

        # 保存到会话历史
        if wxid:
            session = self.session_manager.get_or_create(wxid)
            session.add_message("user", content)
            session.add_message("assistant", f"[生成视频] {video_prompt_text}")

        # 根据 provider 选择生成服务（未指定时随机选择）
        provider = provider or random.choice(VIDEO_PROVIDERS)
        LOG.info(f"使用 {provider} 生成视频")

        if provider.lower() == "openai":
            return await self._generate_openai(video_prompt_text)
        else:
            return await self._generate_gemini(video_prompt_text)

    async def _generate_video_prompt(
            self,
            content: str,
            provider: Optional[str] = None,
            model: Optional[str] = None
    ) -> str:
        """
        使用风格匹配系统生成视频描述词
        
        Args:
            content: 用户原始描述
            provider: LLM 提供商
            model: LLM 模型
            
        Returns:
            英文视频描述词
        """
        try:
            # Step 1: 先尝试快速关键词匹配
            style_id = video_prompt.quick_match_style(content)

            # Step 2: 如果快速匹配没有结果，使用 LLM 进行风格匹配
            if not style_id:
                LOG.info("快速匹配无结果，使用 LLM 进行风格匹配...")
                style_matcher_prompt = video_prompt.get_style_matcher_prompt()

                style_id = await self.llm_router.chat(
                    messages=[
                        {"role": "system", "content": style_matcher_prompt},
                        {"role": "user", "content": content}
                    ],
                    provider=provider,
                    model=model
                )

                # 清理 LLM 返回的风格 ID
                style_id = style_id.strip().lower()

                # 验证风格 ID 是否有效
                valid_ids = video_prompt.get_all_style_ids()
                if style_id not in valid_ids:
                    LOG.warning(f"LLM 返回的风格 ID 无效: {style_id}，使用 general")
                    style_id = "general"

            LOG.info(f"匹配到的视频风格: {style_id}")

            # Step 3: 使用匹配到的风格模板生成最终 prompt
            generator_prompt = video_prompt.get_prompt_generator_prompt(style_id, content)

            video_prompt_text = await self.llm_router.chat(
                messages=[
                    {"role": "system", "content": generator_prompt},
                    {"role": "user", "content": f"请根据以下描述生成视频提示词：{content}"}
                ],
                provider=provider,
                model=model
            )

            LOG.info(f"生成的视频描述词 (风格: {style_id}): {video_prompt_text[:100]}...")
            return video_prompt_text

        except Exception as e:
            LOG.warning(f"生成视频描述词失败，使用原始内容: {e}")
            return content

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

    # ==================== OpenAI Sora (via LiteLLM) ====================

    async def _generate_openai(
            self,
            prompt: str,
            img_data_list: Optional[list[str]] = None
    ) -> VideoResponse:
        """
        使用 OpenAI Sora 生成视频 - 通过 LiteLLM
        API 文档: https://docs.litellm.ai/docs/providers/openai/videos
        
        Args:
            prompt: 视频描述
            img_data_list: 可选，图片 base64 列表（图生视频时使用）
        """
        import litellm
        import tempfile
        import os

        # 获取 API Key
        api_key = None
        if self.config.chatgpt:
            api_key = self.config.chatgpt.key1 or self.config.chatgpt.key2 or self.config.chatgpt.key3

        if not api_key:
            raise ValueError("OpenAI API Key 未配置，无法生成视频呢~")

        model_name = self.config.chatgpt.openai_video_model if self.config.chatgpt else "sora-2"
        # LiteLLM 需要 openai/ 前缀
        litellm_model = f"openai/{model_name}"
        is_img2video = img_data_list and len(img_data_list) > 0
        task_type = "图生视频" if is_img2video else "文生视频"
        LOG.info(f"OpenAI Sora {task_type} (LiteLLM), model: {litellm_model}, prompt: {prompt[:50]}...")

        temp_file = None
        try:
            # 构建请求参数
            gen_params = {
                "model": litellm_model,
                "prompt": prompt,
                "seconds": "8",
                "size": "1280x720",
                "api_key": api_key
            }

            # 如果有图片，保存为临时文件并添加 input_reference
            if is_img2video:
                temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                temp_file.write(base64.b64decode(img_data_list[0]))
                temp_file.close()
                gen_params["input_reference"] = open(temp_file.name, "rb")

            # Step 1: 发起视频生成请求
            try:
                response = await litellm.avideo_generation(**gen_params)
            except litellm.RateLimitError as e:
                LOG.warning(f"OpenAI 视频生成触发速率限制: {e}")
                raise ValueError("呜呜~视频酱今天太累了，等一会再来找我玩吧~")
            video_id_remote = response.id
            LOG.info(f"OpenAI {task_type}任务已创建, video_id: {video_id_remote}")

            # Step 2: 轮询等待完成（OpenAI 可能需要等待）
            max_attempts = 120
            interval = 5.0
            for attempt in range(max_attempts):
                # 尝试下载视频，如果还没完成会失败
                try:
                    video_bytes = await litellm.avideo_content(video_id=video_id_remote, api_key=api_key)
                    if video_bytes:
                        LOG.info(
                            f"[{video_id_remote}] OpenAI {task_type}完成, 大小: {len(video_bytes) / 1024 / 1024:.2f}MB")
                        break
                except litellm.RateLimitError as e:
                    LOG.warning(f"[{video_id_remote}] OpenAI 视频生成触发速率限制: {e}")
                    raise ValueError("呜呜~视频酱今天太累了，等一会再来找我玩吧~")
                except Exception as e:
                    error_str = str(e).lower()
                    # 检查是否是速率限制
                    if any(kw in error_str for kw in ["rate", "quota", "429", "resource_exhausted"]):
                        LOG.warning(f"[{video_id_remote}] OpenAI 视频生成触发速率限制: {str(e)[:200]}")
                        raise ValueError("呜呜~视频酱今天太累了，等一会再来找我玩吧~")
                    # 检查是否是内容安全过滤
                    if any(kw in error_str for kw in ["content_policy", "safety", "filtered", "moderation", "blocked"]):
                        LOG.warning(f"[{video_id_remote}] OpenAI 内容安全过滤触发: {str(e)[:200]}")
                        raise ValueError("生成失败啦! 内容太不堪入目了吧~")
                    # 视频还在处理中
                    LOG.debug(
                        f"[{video_id_remote}] OpenAI {task_type}中... 尝试: {attempt + 1}/{max_attempts}, err: {str(e)[:50]}")
                    await asyncio.sleep(interval)
            else:
                LOG.error(f"[{video_id_remote}] OpenAI {task_type}超时")
                raise ValueError(f"{task_type}超时，请稍后再试~")

            return VideoResponse(
                prompt=prompt,
                video_base64=base64.b64encode(video_bytes).decode()
            )
        finally:
            # 清理临时文件
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)

    # 保持向后兼容
    async def _generate_openai_from_images(
            self,
            prompt: str,
            img_data_list: list[str]
    ) -> VideoResponse:
        """图生视频（兼容方法，调用统一的 _generate_openai）"""
        return await self._generate_openai(prompt, img_data_list)

    # ==================== Gemini Veo (via LiteLLM) ====================

    async def _generate_gemini(
            self,
            prompt: str,
            img_data_list: Optional[list[str]] = None
    ) -> VideoResponse:
        """
        使用 Gemini Veo 生成视频 - 通过 LiteLLM
        
        Args:
            prompt: 视频描述
            img_data_list: 可选，图片 base64 列表（图生视频时使用）
        """
        import litellm
        import tempfile
        import os

        # 获取 API Key
        api_key = None
        if self.config.chatgpt:
            api_key = self.config.chatgpt.gemini_key1

        if not api_key:
            raise ValueError("Gemini API Key 未配置，无法生成视频呢~")

        model_name = self.config.chatgpt.gemini_video_model if self.config.chatgpt else "veo-3.0-generate-preview"
        litellm_model = f"gemini/{model_name}"
        is_img2video = img_data_list and len(img_data_list) > 0
        task_type = "图生视频" if is_img2video else "文生视频"
        LOG.info(f"Gemini Veo {task_type} (LiteLLM), model: {litellm_model}, prompt: {prompt[:50]}...")

        temp_file = None
        try:
            # 构建请求参数
            gen_params = {
                "model": litellm_model,
                "prompt": prompt,
                "size": "1280x720",  # LiteLLM 会转换为 aspectRatio: 16:9
                "seconds": "8",
                "api_key": api_key
            }

            # 如果有图片，保存为临时文件并添加 input_reference
            if is_img2video:
                temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                temp_file.write(base64.b64decode(img_data_list[0]))
                temp_file.close()
                gen_params["input_reference"] = temp_file.name

            # Step 1: 发起视频生成请求
            try:
                response = await litellm.avideo_generation(**gen_params)
            except litellm.RateLimitError as e:
                LOG.warning(f"Gemini 视频生成触发速率限制: {e}")
                raise ValueError("呜呜~视频酱今天太累了，等一会再来找我玩吧~")
            video_id_remote = response.id
            LOG.info(f"Gemini {task_type}任务已创建, video_id: {video_id_remote}")

            # Step 2: 轮询等待完成
            max_attempts = 120
            interval = 5.0
            for attempt in range(max_attempts):
                try:
                    status_response = await litellm.avideo_status(video_id=video_id_remote, api_key=api_key)
                    status = status_response.status

                    if status == "completed":
                        LOG.info(f"[{video_id_remote}] Gemini {task_type}完成, 开始下载...")
                        break
                    elif status == "failed":
                        LOG.error(f"[{video_id_remote}] Gemini {task_type}失败")
                        raise ValueError(f"{task_type}失败啦!")

                    LOG.debug(
                        f"[{video_id_remote}] Gemini {task_type}中... 状态: {status}, 尝试: {attempt + 1}/{max_attempts}")
                    await asyncio.sleep(interval)
                except litellm.RateLimitError as e:
                    LOG.warning(f"[{video_id_remote}] Gemini 视频生成触发速率限制: {e}")
                    raise ValueError("呜呜~视频酱今天太累了，等一会再来找我玩吧~")
                except Exception as e:
                    error_str = str(e).lower()
                    # 检查是否是速率限制
                    if any(kw in error_str for kw in ["rate", "quota", "429", "resource_exhausted"]):
                        LOG.warning(f"[{video_id_remote}] Gemini 视频生成触发速率限制: {str(e)[:200]}")
                        raise ValueError("呜呜~视频酱今天太累了，等一会再来找我玩吧~")
                    # 检查是否是内容安全过滤导致的错误
                    if any(kw in error_str for kw in
                           ["raimediafiltered", "filtered", "generatedsamples", "safety", "policy", "blocked"]):
                        LOG.warning(f"[{video_id_remote}] Gemini 内容安全过滤触发: {str(e)[:200]}")
                        raise ValueError("生成失败啦! 内容太不堪入目了吧~")
                    # 其他错误继续抛出
                    raise
            else:
                LOG.error(f"[{video_id_remote}] Gemini {task_type}超时")
                raise ValueError(f"{task_type}超时，请稍后再试~")

            # Step 3: 下载视频内容并保存到本地
            video_bytes = await litellm.avideo_content(video_id=video_id_remote, api_key=api_key)

            video_id = str(uuid.uuid4())
            video_path = GEN_VIDEO_DIR / f"{video_id}.mp4"
            video_path.write_bytes(video_bytes)
            LOG.info(
                f"[{video_id_remote}] Gemini {task_type}已保存: {video_path}, 大小: {len(video_bytes) / 1024 / 1024:.2f}MB")

            return VideoResponse(
                prompt=prompt,
                video_id=video_id
            )
        finally:
            # 清理临时文件
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)

    # 保持向后兼容
    async def _generate_gemini_from_images(
            self,
            prompt: str,
            img_data_list: list[str]
    ) -> VideoResponse:
        """图生视频（兼容方法，调用统一的 _generate_gemini）"""
        return await self._generate_gemini(prompt, img_data_list)
