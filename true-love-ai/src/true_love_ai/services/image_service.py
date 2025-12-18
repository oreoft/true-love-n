#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像服务模块
提供图像生成、编辑、分析等功能
"""
import base64
import logging
import random
from io import BytesIO
from typing import Optional

import httpx

from true_love_ai.core.config import get_config
from true_love_ai.core.session import get_session_manager
from true_love_ai.llm.router import get_llm_router
from true_love_ai.llm.intent import IntentRouter, ImageOperationType
from true_love_ai.llm import img_prompt
from true_love_ai.models.response import ImageResponse

LOG = logging.getLogger(__name__)

# ==================== Stability AI 配置 ====================
SD_BASE_URL = "https://api.stability.ai/v2beta/stable-image"
SD_GENERATE_URL = f"{SD_BASE_URL}/generate/ultra"
SD_CONTROL_URL = f"{SD_BASE_URL}/control/structure"
SD_ERASE_URL = f"{SD_BASE_URL}/edit/erase"
SD_REPLACE_URL = f"{SD_BASE_URL}/edit/search-and-replace"
SD_REMOVE_BG_URL = f"{SD_BASE_URL}/edit/remove-background"

# 图像操作类型到 URL 的映射
SD_URL_MAP = {
    'gen_by_img': SD_CONTROL_URL,
    'erase_img': SD_ERASE_URL,
    'replace_img': SD_REPLACE_URL,
    'remove_background_img': SD_REMOVE_BG_URL
}


class ImageService:
    """
    图像服务
    支持多种图像提供商：OpenAI、Stability AI、Gemini
    """

    def __init__(self):
        self.config = get_config()
        self.llm_router = get_llm_router()
        self.intent_router = IntentRouter()
        self.session_manager = get_session_manager()

        # Stability AI API Key
        self.sd_api_key = self.config.platform_key.sd if self.config.platform_key else ""

    async def get_img_type(
            self,
            content: str,
            provider: Optional[str] = None,
            model: Optional[str] = None
    ) -> dict:
        """
        判断图像操作类型
        
        Args:
            content: 用户描述
            provider: 提供商
            model: 模型
            
        Returns:
            {"type": str, "answer": str}
        """
        LOG.info(f"开始判断图像操作类型: {content[:50]}...")

        intent = await self.intent_router.route_image(
            content=content,
            provider=provider,
            model=model
        )

        return {
            "type": intent.type.value,
            "answer": intent.answer
        }

    async def generate_image(
            self,
            content: str,
            img_data: Optional[str] = None,
            wxid: str = "",
            sender: str = "",
            provider: Optional[str] = None,
            model: Optional[str] = None
    ) -> ImageResponse:
        """
        生成图像
        
        Args:
            content: 图像描述或操作指令
            img_data: base64 图像（图生图时使用）
            wxid: 会话 ID
            sender: 发送者
            provider: 提供商 (openai/stability/gemini)
            model: 模型
            
        Returns:
            ImageResponse
        """
        if img_data:
            # 图生图 - 先解析内容获取类型和 prompt
            if isinstance(content, dict):
                operation_type = content.get("type", "gen_by_img")
                prompt = content.get("answer", "")
            else:
                # 需要先判断操作类型
                intent = await self.intent_router.route_image(content, provider, model)
                operation_type = intent.type.value
                prompt = intent.answer

            return await self._edit_image(
                img_data=img_data,
                operation_type=operation_type,
                prompt=prompt,
                provider=provider
            )
        else:
            # 文生图
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
    ) -> ImageResponse:
        """
        文生图
        
        Args:
            content: 用户描述
            wxid: 会话 ID
            provider: 提供商
            model: 模型
        """
        LOG.info(f"开始文生图: {content[:50]}...")

        # 使用新的提示词系统生成图像描述词
        image_prompt = await self._generate_image_prompt(
            content=content,
            provider=provider,
            model=model
        )

        # 保存到会话历史
        if wxid:
            session = self.session_manager.get_or_create(wxid)
            session.add_message("user", content)
            session.add_message("assistant", f"[生成图片] {image_prompt}")

        # 根据 provider 选择生图服务（未指定时随机选择）
        provider = provider or random.choice(["openai", "stability", "gemini"])
        LOG.info(f"使用 {provider} 生成图像")

        if provider.lower() == "openai":
            return await self._generate_openai(image_prompt)
        elif provider.lower() == "gemini":
            return await self._generate_gemini(image_prompt)
        else:
            return await self._generate_stability(image_prompt)

    async def _generate_image_prompt(
            self,
            content: str,
            provider: Optional[str] = None,
            model: Optional[str] = None
    ) -> str:
        """
        使用风格匹配系统生成图像描述词
        
        Args:
            content: 用户原始描述
            provider: LLM 提供商
            model: LLM 模型
            
        Returns:
            英文图像描述词
        """
        try:
            # Step 1: 先尝试快速关键词匹配
            style_id = img_prompt.quick_match_style(content)
            
            # Step 2: 如果快速匹配没有结果，使用 LLM 进行风格匹配
            if not style_id:
                LOG.info("快速匹配无结果，使用 LLM 进行风格匹配...")
                style_matcher_prompt = img_prompt.get_style_matcher_prompt()
                
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
                valid_ids = img_prompt.get_all_style_ids()
                if style_id not in valid_ids:
                    LOG.warning(f"LLM 返回的风格 ID 无效: {style_id}，使用 general")
                    style_id = "general"
            
            LOG.info(f"匹配到的风格: {style_id}")
            
            # Step 3: 使用匹配到的风格模板生成最终 prompt
            generator_prompt = img_prompt.get_prompt_generator_prompt(style_id, content)
            
            image_prompt = await self.llm_router.chat(
                messages=[
                    {"role": "system", "content": generator_prompt},
                    {"role": "user", "content": f"请根据以下描述生成图像提示词：{content}"}
                ],
                provider=provider,
                model=model
            )
            
            LOG.info(f"生成的图像描述词 (风格: {style_id}): {image_prompt[:100]}...")
            return image_prompt
            
        except Exception as e:
            LOG.warning(f"生成描述词失败，使用原始内容: {e}")
            return content

    async def _generate_stability(self, prompt: str) -> ImageResponse:
        """使用 Stability AI 生成图像"""
        LOG.info(f"Stability AI 生成图像, model: ultra, prompt: {prompt[:50]}...")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                SD_GENERATE_URL,
                headers={
                    "authorization": f"Bearer {self.sd_api_key}",
                    "accept": "application/json"
                },
                files={"none": ""},
                data={
                    "prompt": prompt,
                    "output_format": "jpeg",
                    "aspect_ratio": "1:1"
                },
                timeout=120.0
            )

            if response.status_code == 200:
                return ImageResponse(
                    prompt=prompt,
                    img=response.json()['image']
                )
            else:
                LOG.error(f"Stability AI 生成失败: {response.status_code}, {response.text}")
                raise ValueError("生成失败啦! 内容太不堪入目了吧~")

    async def _generate_openai(self, prompt: str) -> ImageResponse:
        """
        使用 OpenAI 生成图像 - 通过 LiteLLM
        支持 gpt-image-1, dall-e-3, dall-e-2
        """
        import litellm

        # 获取 API Key
        api_key = None
        if self.config.chatgpt:
            api_key = self.config.chatgpt.key1 or self.config.chatgpt.key2 or self.config.chatgpt.key3

        if not api_key:
            raise ValueError("OpenAI API Key 未配置，无法生成图像呢~")

        # 获取模型配置
        image_model = self.config.chatgpt.image_model if self.config.chatgpt else "gpt-image-1"
        LOG.info(f"OpenAI 生成图像 (LiteLLM), model: {image_model}, prompt: {prompt[:50]}...")

        try:
            response = await litellm.aimage_generation(
                model=image_model,
                prompt=prompt,
                n=1,
                size="1024x1024",
                response_format="b64_json",
                api_key=api_key
            )

            # LiteLLM 返回格式
            if response.data and len(response.data) > 0:
                image_data = response.data[0].b64_json
                if image_data:
                    return ImageResponse(
                        prompt=prompt,
                        img=image_data
                    )

            LOG.error(f"OpenAI 返回数据格式异常: {response}")
            raise ValueError("生成失败啦! 返回数据异常~")

        except litellm.exceptions.ContentPolicyViolationError:
            raise ValueError("生成失败啦! 内容不太合适呢，换个描述试试吧~")
        except litellm.exceptions.Timeout:
            LOG.error("OpenAI 图像生成超时")
            raise ValueError("生成超时啦! 稍后再试试吧~")
        except ValueError:
            raise
        except Exception as e:
            LOG.error(f"OpenAI 图像生成异常: {e}")
            raise ValueError(f"生成失败啦! {str(e)[:100]}")

    async def _generate_gemini(self, prompt: str) -> ImageResponse:
        """
        使用 Gemini 生成图像 - 通过 LiteLLM
        支持 imagen-4.0-generate-001, gemini-3-pro-image-preview 等
        """
        import litellm

        # 获取 API Key
        api_key = None
        if self.config.chatgpt:
            api_key = self.config.chatgpt.gemini_key1

        if not api_key:
            raise ValueError("Gemini API Key 未配置，无法生成图像呢~")

        # Gemini Image 模型，LiteLLM 需要 gemini/ 前缀
        model_name = self.config.chatgpt.gemini_image_model if self.config.chatgpt else "imagen-4.0-generate-001"
        litellm_model = f"gemini/{model_name}"
        LOG.info(f"Gemini 生成图像 (LiteLLM), model: {litellm_model}, prompt: {prompt[:50]}...")

        try:
            response = await litellm.aimage_generation(
                model=litellm_model,
                prompt=prompt,
                n=1,
                api_key=api_key
            )

            # LiteLLM 返回格式 - Gemini 返回 URL 或 b64_json
            if response.data and len(response.data) > 0:
                image_item = response.data[0]
                # 优先使用 b64_json，否则下载 URL
                if hasattr(image_item, 'b64_json') and image_item.b64_json:
                    return ImageResponse(
                        prompt=prompt,
                        img=image_item.b64_json
                    )
                elif hasattr(image_item, 'url') and image_item.url:
                    # 下载图片并转为 base64
                    import httpx
                    async with httpx.AsyncClient() as client:
                        img_resp = await client.get(image_item.url, timeout=60.0)
                        if img_resp.status_code == 200:
                            import base64
                            return ImageResponse(
                                prompt=prompt,
                                img=base64.b64encode(img_resp.content).decode()
                            )

            LOG.error(f"Gemini 返回数据格式异常: {response}")
            raise ValueError("生成失败啦! 返回数据异常~")

        except litellm.exceptions.ContentPolicyViolationError:
            raise ValueError("生成失败啦! 内容不太合适呢，换个描述试试吧~")
        except ValueError:
            raise
        except Exception as e:
            LOG.error(f"Gemini 图像生成异常: {e}")
            raise ValueError(f"生成失败啦! {str(e)[:100]}")

    async def _edit_image(
            self,
            img_data: str,
            operation_type: str,
            prompt: str,
            provider: Optional[str] = None
    ) -> ImageResponse:
        """
        编辑图像
        
        Args:
            img_data: base64 图像
            operation_type: 操作类型
            prompt: 操作描述
            provider: 提供商
        """
        LOG.info(f"编辑图像: type={operation_type}, prompt={prompt[:50]}...")

        # 目前只支持 Stability AI
        url = SD_URL_MAP.get(operation_type, SD_CONTROL_URL)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={
                    "authorization": f"Bearer {self.sd_api_key}",
                    "accept": "application/json"
                },
                files={
                    "image": BytesIO(base64.b64decode(img_data))
                },
                data={
                    "prompt": prompt,
                    "search_prompt": prompt,
                    "control_strength": 0.7,
                    "output_format": "png"
                },
                timeout=120.0
            )

            if response.status_code == 200:
                return ImageResponse(
                    prompt=prompt,
                    img=response.json()['image']
                )
            else:
                LOG.error(f"Stability AI 编辑失败: {response.status_code}, {response.text}")
                raise ValueError("编辑失败啦! 可能是图片太奇怪了~")

    async def analyze_image(
            self,
            content: str,
            img_data: str,
            wxid: str = "",
            sender: str = "",
            provider: Optional[str] = None,
            model: Optional[str] = None
    ) -> str:
        """
        分析图像
        
        Args:
            content: 问题
            img_data: base64 图像
            wxid: 会话 ID
            sender: 发送者
            provider: 提供商
            model: 模型
            
        Returns:
            分析结果
        """
        LOG.info(f"开始分析图像: {content[:50]}...")

        # 处理 debug 模式
        is_debug = content.startswith("debug")
        clean_content = content.replace("debug", "", 1).strip() if is_debug else content

        # 获取系统 prompt
        analyze_prompt = self.config.chatgpt.prompt6 if self.config.chatgpt else "请分析这张图片"

        # 构建带系统提示的问题
        full_prompt = f"{analyze_prompt}\n\n用户问题: {clean_content}"

        # 调用 Vision
        result = await self.llm_router.vision(
            prompt=full_prompt,
            image_data=img_data,
            provider=provider,
            model=model
        )

        # 保存到会话历史
        if wxid:
            session = self.session_manager.get_or_create(wxid)
            session.add_message("user", clean_content)
            session.add_message("assistant", result)

        if is_debug:
            result = f"{result}\n\n(provider: {provider or 'default'}, model: {model or 'default'})"

        return result
