#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 模块
提供大语言模型相关服务
"""
from true_love_ai.llm.service import LLMService, name, fetch_stream
from true_love_ai.llm.constants import (
    OPENAI_MODEL, OPENAI_VISION_MODEL, CLAUDE_MODEL, DEEPSEEK_MODEL, DEFAULT_MODEL
)

# 兼容性别名
ChatGPT = LLMService

__all__ = [
    'LLMService',
    'ChatGPT',
    'name',
    'fetch_stream',
    'OPENAI_MODEL',
    'OPENAI_VISION_MODEL', 
    'CLAUDE_MODEL',
    'DEEPSEEK_MODEL',
    'DEFAULT_MODEL',
]
