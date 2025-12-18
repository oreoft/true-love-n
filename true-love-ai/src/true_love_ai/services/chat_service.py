#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聊天服务模块
处理用户对话
"""
import json
import logging
import time
from typing import Optional

from true_love_ai.core.config import get_config
from true_love_ai.core.session import get_session_manager
from true_love_ai.llm.router import get_llm_router
from true_love_ai.llm.intent import IntentRouter, IntentType
from true_love_ai.models.response import ChatResponse
from true_love_ai.services.search_service import fetch_baidu_references

LOG = logging.getLogger(__name__)


class ChatService:
    """
    聊天服务
    处理用户对话，包含意图识别、搜索增强等功能
    """
    
    def __init__(self):
        self.config = get_config()
        self.session_manager = get_session_manager()
        self.llm_router = get_llm_router()
        self.intent_router = IntentRouter()
    
    async def get_answer(
        self,
        content: str,
        session_id: str,
        sender: str = "",
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> ChatResponse:
        """
        获取聊天回答
        
        Args:
            content: 用户消息
            session_id: 会话 ID
            sender: 发送者
            provider: 模型提供商
            model: 模型名称
            
        Returns:
            ChatResponse
        """
        start_time = time.time()
        
        # 处理 debug 模式
        is_debug = content.startswith("debug")
        clean_content = content.replace("debug", "", 1).strip() if is_debug else content
        
        if not clean_content:
            clean_content = "你好"
        
        # 获取或创建会话
        session = self.session_manager.get_or_create(session_id)
        
        LOG.info(f"开始调用 LLM, session={session_id}, provider={provider}, model={model}")
        
        # 意图识别（带上下文，理解指代关系和时间敏感查询）
        intent_messages = session.get_context_for_intent(clean_content)
        intent_result = await self.intent_router.route(
            messages=intent_messages,
            provider=provider,
            model=model
        )
        
        # 根据意图处理
        if intent_result.type == IntentType.CHAT:
            # 普通聊天：存入历史，带历史调用 LLM
            session.add_message("user", clean_content)
            messages = session.get_messages_for_llm()
            answer = await self.llm_router.chat(
                messages=messages,
                provider=provider,
                model=model,
                stream=True
            )
            session.add_message("assistant", answer)
            response_type = "chat"
            
        elif intent_result.type == IntentType.SEARCH:
            # 搜索增强：存入历史，带历史调用 LLM
            session.add_message("user", clean_content)
            messages = session.get_messages_for_llm()
            answer = await self._handle_search(
                original_content=clean_content,
                search_query=intent_result.answer,
                messages=messages,
                provider=provider,
                model=model
            )
            # 搜索回答只保存纯回答部分，不保存搜索尾巴
            pure_answer = answer.split("\n- - - - - - - - - - - -")[0]
            session.add_message("assistant", pure_answer)
            response_type = "chat"
            
        elif intent_result.type == IntentType.GEN_IMAGE:
            # 生图意图：不存入 session，避免干扰后续聊天
            answer = intent_result.answer
            response_type = "gen-img"

        elif intent_result.type == IntentType.GEN_VIDEO:
            # 生视频意图：不存入 session，避免干扰后续聊天
            answer = intent_result.answer
            response_type = "gen-video"

        else:
            answer = intent_result.answer or "呜呜，我不太明白你的意思呢~"
            response_type = "chat"
        
        cost = round(time.time() - start_time, 2)
        LOG.info(f"回答耗时: {cost}s, type={response_type}")
        
        # 构建响应
        response = ChatResponse(type=response_type, answer=answer)
        
        if is_debug:
            response.debug = f"(aiCost: {cost}s, provider: {provider or 'default'}, model: {model or 'default'})"
        
        return response
    
    async def _handle_search(
        self,
        original_content: str,
        search_query: str,
        messages: list[dict],
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        """
        处理搜索请求
        
        Args:
            original_content: 原始问题
            search_query: 搜索关键词
            messages: 对话历史
            provider: 提供商
            model: 模型
            
        Returns:
            搜索增强后的回答
        """
        LOG.info(f"搜索增强: query={search_query}")
        
        # 执行百度搜索
        reference_list = fetch_baidu_references(search_query)
        LOG.info(f"搜索结果数量: {len(reference_list)}")
        
        # 构建搜索增强消息
        refer_content = f"针对这个回答, 参考信息和来源链接如下: {json.dumps(reference_list, ensure_ascii=False)}"
        
        search_system_prompt = (
            "下面你的回答必须结合上下文,因为上下文都是联网查询的,尤其是assistant的来源和参考链接，"
            "所以相当于你可以联网获取信息, 所以不允许说你不能联网, "
            "如果assistant的参考是一个空list, 你就说联网查询超时了, 引导用户再问一遍"
            "另外如果你不知道回答，请不要不要胡说. "
            "如果用户要求文章或者链接请你把最相关的参考链接给出(参考链接必须在上下文出现过)"
        )
        
        # 构建增强后的消息列表
        enhanced_messages = messages + [
            {"role": "assistant", "content": refer_content},
            {"role": "system", "content": search_system_prompt},
            {"role": "user", "content": original_content}
        ]
        
        # 再次调用 LLM 生成回答
        answer = await self.llm_router.chat(
            messages=enhanced_messages,
            provider=provider,
            model=model,
            stream=True
        )
        
        # 添加搜索尾巴
        search_tail = f"\n- - - - - - - - - - - -\n\n🐾💩🕵：{search_query}"
        
        return answer + search_tail
    
    async def get_xun_wen(
        self,
        question: str,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        """
        询问功能（特定格式问题）
        
        Args:
            question: 格式为 "询问-实际问题"
            provider: 提供商
            model: 模型
            
        Returns:
            回答文本
        """
        content = question.split("-")[1] if "-" in question else question
        
        config = get_config()
        xunwen_prompt = config.chatgpt.prompt3 if config.chatgpt else "你是一个智能助手"
        
        answer = await self.llm_router.chat(
            messages=[
                {"role": "system", "content": xunwen_prompt},
                {"role": "user", "content": content}
            ],
            provider=provider,
            model=model
        )
        
        return answer
