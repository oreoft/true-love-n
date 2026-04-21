#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM 路由模块：所有调用通过 LiteLLM，模型由 ModelRegistry 统一管理"""
import logging
from typing import Optional

import litellm

from true_love_ai.core.model_registry import get_model_registry

LOG = logging.getLogger(__name__)


class LLMRouter:

    def _model(self, category: str, key: str = "default") -> str:
        return get_model_registry().get(category, key)

    async def chat(
            self,
            messages: list[dict],
            model: Optional[str] = None,
            stream: bool = False,
            **kwargs,
    ) -> str:
        resolved = model or self._model("chat")
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

    async def chat_for_agent(
            self,
            messages: list[dict],
            tools: list[dict],
            model: Optional[str] = None,
    ) -> tuple[str, list | None]:
        import json as _json
        resolved = model or self._model("chat")
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
            model: Optional[str] = None,
            **kwargs,
    ) -> str:
        resolved = model or self._model("vision")
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
        resolved = self._model("compress")
        LOG.info("compress: model=%s", resolved)
        response = await litellm.acompletion(model=resolved, messages=messages, stream=False)
        return response.choices[0].message.content


_llm_router: Optional[LLMRouter] = None


def get_llm_router() -> LLMRouter:
    global _llm_router
    if _llm_router is None:
        _llm_router = LLMRouter()
    return _llm_router
