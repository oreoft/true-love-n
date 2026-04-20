#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM 路由模块：所有调用通过 LiteLLM 代理，模型由 ModelRegistry 统一管理"""
import logging
from typing import Optional

import litellm

from true_love_ai.core.model_registry import get_model_registry

LOG = logging.getLogger(__name__)


class LLMRouter:

    def _model(self, category: str, key: str = "openai") -> str:
        return get_model_registry().get(category, key)

    async def chat(
            self,
            messages: list[dict],
            provider: str = "openai",
            model: Optional[str] = None,
            stream: bool = False,
            **kwargs,
    ) -> str:
        resolved = model or self._model("chat", provider)
        LOG.info("chat: model=%s msgs=%d", resolved, len(messages))

        response = await litellm.acompletion(
            model=resolved, messages=messages, stream=stream, **kwargs
        )
        if stream:
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
            tool_choice,
            provider: str = "openai",
            model: Optional[str] = None,
            **kwargs,
    ) -> str:
        resolved = model or self._model("chat", provider)
        LOG.info("chat_with_tools: model=%s tools=%s", resolved, [t["function"]["name"] for t in tools])

        response = await litellm.acompletion(
            model=resolved, messages=messages,
            tools=tools, tool_choice=tool_choice, stream=True, **kwargs
        )

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
            args_dict = {"_answer": content.strip()} if (not fn_name and content) else (
                _json.loads(arguments) if arguments else {}
            )
        except Exception:
            args_dict = {}
        args_dict["_fn_name"] = fn_name
        return _json.dumps(args_dict, ensure_ascii=False)

    async def chat_for_agent(
            self,
            messages: list[dict],
            tools: list[dict],
            provider: str = "openai",
            model: Optional[str] = None,
    ) -> tuple[str, list | None]:
        import json as _json
        resolved = model or self._model("chat", provider)
        LOG.info("agent: model=%s tools=%d msgs=%d", resolved, len(tools), len(messages))

        response = await litellm.acompletion(
            model=resolved,
            messages=messages,
            tools=tools or None,
            tool_choice="auto" if tools else None,
            stream=False,
        )
        message = response.choices[0].message

        if message.tool_calls:
            calls = []
            for tc in message.tool_calls:
                try:
                    args = _json.loads(tc.function.arguments) if tc.function.arguments else {}
                except Exception:
                    args = {}
                calls.append({"id": tc.id, "name": tc.function.name, "arguments": args, "_raw": tc})
            return "tool_calls", calls

        return "text", message.content or ""

    async def vision(
            self,
            prompt: str,
            image_data: str,
            provider: str = "openai",
            model: Optional[str] = None,
            **kwargs,
    ) -> str:
        resolved = model or self._model("vision", provider)
        LOG.info("vision: model=%s", resolved)
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}},
            ],
        }]
        return await self.chat(messages, model=resolved, **kwargs)

    async def compress(self, messages: list[dict]) -> str:
        resolved = self._model("compress", "openai")
        LOG.info("compress: model=%s", resolved)
        response = await litellm.acompletion(model=resolved, messages=messages, stream=False)
        return response.choices[0].message.content


_llm_router: Optional[LLMRouter] = None


def get_llm_router() -> LLMRouter:
    global _llm_router
    if _llm_router is None:
        _llm_router = LLMRouter()
    return _llm_router
