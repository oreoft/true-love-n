#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 路由模块
使用 LiteLLM 进行多模型路由和负载均衡
"""
import logging
from typing import Optional

import litellm

from true_love_ai.core.config import get_config

LOG = logging.getLogger(__name__)


class LLMRouter:
    """LLM 路由器 - 使用 LiteLLM 实现多模型支持和负载均衡"""

    def __init__(self):
        self.config = get_config().chatgpt
        self.platform_key = get_config().platform_key

    def _resolve_model(self, provider: Optional[str] = None, model: Optional[str] = None) -> str:
        """解析模型名称：优先用指定 model，其次按 provider 选择，最后用默认"""
        if model:
            return "openai/" + model

        if provider and self.config:
            provider_map = {
                "openai": self.config.default_model,
                "claude": self.config.claude_model,
                "deepseek": self.config.deepseek_model,
                "gemini": self.config.gemini_model,
            }
            return "openai/" + provider.lower() + "/" + provider_map.get(provider.lower(), self.config.default_model)

        return "openai/" + self.config.default_model if self.config else "gpt-4o"

    async def chat(
            self,
            messages: list[dict],
            provider: Optional[str] = None,
            model: Optional[str] = None,
            stream: bool = False,
            **kwargs
    ) -> str:
        """发送聊天请求"""
        resolved_model = self._resolve_model("openai", model)
        LOG.info(f"LLM chat: model={resolved_model}, messages_count={len(messages)}")

        response = await litellm.acompletion(
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
            tool_choice,   # str | dict
            provider: Optional[str] = None,
            model: Optional[str] = None,
            **kwargs
    ) -> str:
        """
        带工具调用的聊天。

        返回 JSON 字符串，包含两个字段：
        - 工具参数（昦平展开）
        - _fn_name: 被调用的 function 名称
        """
        resolved_model = self._resolve_model(provider, model)
        LOG.info(f"LLM chat_with_tools: model={resolved_model}, tools={[t['function']['name'] for t in tools]}")

        response = await litellm.acompletion(
            model=resolved_model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            stream=True,
            **kwargs
        )

        # 提取工具调用名称和参数及可能的文本
        fn_name = ""
        arguments = ""
        content = ""
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.tool_calls:
                tc = delta.tool_calls[0]
                if tc.function.name:
                    fn_name = tc.function.name
                if tc.function.arguments:
                    arguments += tc.function.arguments
            elif delta.content:
                content += delta.content

        import json as _json
        try:
            # 如果大模型吐出了正常文本代替工具调用，我们就把它包一层特定的结构返回
            if not fn_name and not arguments and content:
                args_dict = {"_answer": content.strip()}
            else:
                args_dict = _json.loads(arguments) if arguments else {}
        except Exception:
            args_dict = {}

        # 将 _fn_name 注入返回内容，便于调用方判断是哪个 tool
        args_dict["_fn_name"] = fn_name
        return _json.dumps(args_dict, ensure_ascii=False)

    async def chat_for_agent(
            self,
            messages: list[dict],
            tools: list[dict],
            provider: Optional[str] = None,
            model: Optional[str] = None,
    ) -> tuple[str, list[dict] | None]:
        """
        Agent Loop 专用：调用 LLM 并返回结构化结果。

        Returns:
            ("text", None)       — LLM 返回了文本答案
            ("tool_calls", [...])— LLM 要调用工具，list 中每个元素：
                                   {"id": str, "name": str, "arguments": dict}
        """
        import json as _json

        resolved_model = self._resolve_model(provider, model)
        LOG.info("Agent LLM call: model=%s, tools=%d, msgs=%d",
                 resolved_model, len(tools), len(messages))

        response = await litellm.acompletion(
            model=resolved_model,
            messages=messages,
            tools=tools or None,
            tool_choice="auto" if tools else None,
            stream=False,
        )

        message = response.choices[0].message

        # LLM 要调用工具
        if message.tool_calls:
            calls = []
            for tc in message.tool_calls:
                try:
                    args = _json.loads(tc.function.arguments) if tc.function.arguments else {}
                except Exception:
                    args = {}
                calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": args,
                    # 保存原始 tool_call 结构，供拼装 assistant message 使用
                    "_raw": tc,
                })
            return "tool_calls", calls

        # LLM 返回文本
        content = message.content or ""
        return "text", content

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
