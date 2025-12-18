#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 路由模块
使用 LiteLLM 进行多模型路由和负载均衡
"""
import logging
from typing import Optional

import litellm
from litellm import Router

from true_love_ai.core.config import get_config

LOG = logging.getLogger(__name__)

# LiteLLM 配置
litellm.modify_params = True
litellm.drop_params = True


class LLMRouter:
    """LLM 路由器 - 使用 LiteLLM 实现多模型支持和负载均衡"""
    
    def __init__(self):
        self.config = get_config().chatgpt
        self.router = self._init_router()
    
    def _init_router(self) -> Optional[Router]:
        """初始化 LiteLLM 路由器"""
        if not self.config:
            return None
        
        model_list = []
        
        # OpenAI 多 Key 负载均衡
        openai_keys = [getattr(self.config, f'key{i}', '') for i in range(1, 4)]
        for key in filter(None, openai_keys):
            for model in [self.config.default_model, self.config.vision_model]:
                model_list.append({
                    "model_name": model,
                    "litellm_params": {"model": model, "api_key": key}
                })
        
        # 其他提供商（单 Key）
        providers = [
            ("claude_key1", self.config.claude_model, None),
            ("ds_key1", self.config.deepseek_model, None),
            # Gemini 需要加 gemini/ 前缀使用 Google AI Studio API（而不是 Vertex AI）
            ("gemini_key1", self.config.gemini_model, "gemini/"),
        ]
        for key_attr, model, prefix in providers:
            key = getattr(self.config, key_attr, '')
            if key:
                # litellm_params.model 可能需要前缀，但 model_name 保持原样
                litellm_model = f"{prefix}{model}" if prefix else model
                model_list.append({
                    "model_name": model,
                    "litellm_params": {"model": litellm_model, "api_key": key}
                })
        
        LOG.info(f"LLM Router 初始化，共 {len(model_list)} 个模型配置")
        return Router(model_list=model_list) if model_list else None
    
    def _resolve_model(self, provider: Optional[str] = None, model: Optional[str] = None) -> str:
        """解析模型名称：优先用指定 model，其次按 provider 选择，最后用默认"""
        if model:
            return model
        
        if provider and self.config:
            provider_map = {
                "openai": self.config.default_model,
                "claude": self.config.claude_model,
                "deepseek": self.config.deepseek_model,
                "gemini": self.config.gemini_model,
            }
            return provider_map.get(provider.lower(), self.config.default_model)
        
        return self.config.default_model if self.config else "gpt-4o"
    
    async def chat(
        self,
        messages: list[dict],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> str:
        """发送聊天请求"""
        resolved_model = self._resolve_model(provider, model)
        LOG.info(f"LLM chat: model={resolved_model}, messages_count={len(messages)}")
        
        if not self.router:
            raise RuntimeError("LLM Router 未初始化，请检查配置")
        
        response = await self.router.acompletion(
            model=resolved_model,
            messages=messages,
            stream=stream,
            **kwargs
        )
        
        if stream:
            # 流式响应：拼接完整内容
            result = ""
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    result += chunk.choices[0].delta.content
            return result
        
        return response.choices[0].message.content
    
    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        tool_choice: dict,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """带工具调用的聊天，返回工具调用参数"""
        resolved_model = self._resolve_model(provider, model)
        LOG.info(f"LLM chat_with_tools: model={resolved_model}")
        
        if not self.router:
            raise RuntimeError("LLM Router 未初始化，请检查配置")
        
        response = await self.router.acompletion(
            model=resolved_model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            stream=True,
            **kwargs
        )
        
        # 提取工具调用参数
        result = ""
        async for chunk in response:
            if chunk.choices[0].delta.tool_calls:
                tool_call = chunk.choices[0].delta.tool_calls[0]
                if tool_call.function.arguments:
                    result += tool_call.function.arguments
        return result
    
    async def vision(
        self,
        prompt: str,
        image_data: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """视觉理解 - 分析图像内容"""
        # 确定 vision 模型
        if model:
            resolved_model = model
        elif provider and provider.lower() != "openai" and self.config:
            vision_map = {"claude": self.config.claude_model, "gemini": self.config.gemini_model}
            resolved_model = vision_map.get(provider.lower(), self.config.vision_model)
        else:
            resolved_model = self.config.vision_model if self.config else "gpt-4o"
        
        LOG.info(f"LLM vision: model={resolved_model}")
        
        # 构建 vision 消息格式
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
            ]
        }]
        
        return await self.chat(messages, model=resolved_model, **kwargs)


# 全局单例
_llm_router: Optional[LLMRouter] = None


def get_llm_router() -> LLMRouter:
    """获取 LLM 路由器单例"""
    global _llm_router
    if _llm_router is None:
        _llm_router = LLMRouter()
    return _llm_router
