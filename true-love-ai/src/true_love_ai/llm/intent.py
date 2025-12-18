#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
意图识别模块
使用 OpenAI Function Call 进行意图识别

设计原则：
1. 上下文感知：传递最近对话历史，理解指代关系
2. 时间感知：传递当前时间，让时间敏感查询补充年份
3. 搜索优化：生成完整、具体的搜索关键词
"""
import json
import logging
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from true_love_ai.llm.router import get_llm_router
from true_love_ai.llm.function_calls import TYPE_ANSWER_CALL, IMG_TYPE_ANSWER_CALL

LOG = logging.getLogger(__name__)


class IntentType(str, Enum):
    """意图类型"""
    CHAT = "chat"
    SEARCH = "search"
    GEN_IMAGE = "gen-img"


class ChatIntent(BaseModel):
    """聊天意图识别结果"""
    type: IntentType = Field(description="意图类型")
    answer: str = Field(description="回答内容/搜索关键词/图像描述")


class ImageOperationType(str, Enum):
    """图像操作类型"""
    GEN_BY_IMG = "gen_by_img"
    ERASE_IMG = "erase_img"
    REPLACE_IMG = "replace_img"
    ANALYZE_IMG = "analyze_img"
    REMOVE_BACKGROUND = "remove_background_img"


class ImageIntent(BaseModel):
    """图像操作意图"""
    type: ImageOperationType = Field(description="操作类型")
    answer: str = Field(description="操作描述词")


class IntentRouter:
    """
    意图路由器
    使用 Function Call 进行上下文感知的意图识别
    """
    
    def __init__(self):
        self.llm_router = get_llm_router()
    
    async def route(
        self,
        messages: list[dict],
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> ChatIntent:
        """
        路由用户消息到对应意图（上下文感知版本）
        
        Args:
            messages: 包含上下文的消息列表（由 session.get_context_for_intent 生成）
            provider: 提供商
            model: 模型
            
        Returns:
            ChatIntent: 意图识别结果
        """
        try:
            result_str = await self.llm_router.chat_with_tools(
                messages=messages,
                tools=TYPE_ANSWER_CALL,
                tool_choice={"type": "function", "function": {"name": "type_answer"}},
                provider=provider,
                model=model
            )
            
            result = json.loads(result_str)
            LOG.info(f"意图识别结果: {result}")
            
            return ChatIntent(
                type=IntentType(result.get("type", "chat")),
                answer=result.get("answer", "")
            )
            
        except Exception as e:
            LOG.exception(f"意图识别失败: {e}")
            # 降级为普通 chat，返回空答案让后续流程处理
            return ChatIntent(
                type=IntentType.CHAT,
                answer=""
            )
    
    async def route_image(
        self,
        content: str,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> ImageIntent:
        """
        路由图像操作意图
        
        Args:
            content: 用户描述
            provider: 提供商
            model: 模型
            
        Returns:
            ImageIntent: 图像操作意图
        """
        try:
            config = self.llm_router.config
            system_prompt = config.prompt5 if config else "根据用户描述判断图像操作类型"
            
            result_str = await self.llm_router.chat_with_tools(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ],
                tools=IMG_TYPE_ANSWER_CALL,
                tool_choice={"type": "function", "function": {"name": "img_type_answer_call"}},
                provider=provider,
                model=model
            )
            
            result = json.loads(result_str)
            LOG.info(f"图像意图识别结果: {result}")
            
            return ImageIntent(
                type=ImageOperationType(result.get("type", "analyze_img")),
                answer=result.get("answer", content)
            )
            
        except Exception as e:
            LOG.exception(f"图像意图识别失败: {e}")
            # 默认为分析图像
            return ImageIntent(
                type=ImageOperationType.ANALYZE_IMG,
                answer=content
            )
