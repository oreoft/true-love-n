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
from true_love_ai.llm.intent import IntentRouter, IntentType
from true_love_ai.llm.router import get_llm_router
from true_love_ai.models.response import ChatResponse
from true_love_ai.services.search_service import SearchService

LOG = logging.getLogger(__name__)
search_client = SearchService('baidu', None)


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
        intent_start_time = time.time()
        intent_messages = session.get_context_for_intent(clean_content)
        intent_result = await self.intent_router.route(
            messages=intent_messages,
            provider=provider,
            model=model
        )
        LOG.info("意图识别耗时: %.2fs", round(time.time() - intent_start_time, 2))

        # 根据意图处理
        if intent_result.type == IntentType.CHAT:
            # 普通聊天：存入历史，带历史调用 LLM
            session.add_message("user", clean_content)
            answer = intent_result.answer
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

        elif intent_result.type == IntentType.WECHAT_QR:
            # 微信扫码连通道意图：调用 Nexu 接口获取二维码
            import httpx
            nexu_config = self.config.nexu
            url = f"{nexu_config.base_url}/api/v1/channels/wechat/qr-start"
            LOG.info(f"调用 Nexu 接口: {url}")
            try:
                async with httpx.AsyncClient() as client:
                    # 也可以带上 token 如果配置了的话
                    headers = {}
                    if nexu_config.token:
                        headers["Authorization"] = f"Bearer {nexu_config.token}"

                    res = await client.post(url, headers=headers, timeout=30.0)
                    res.raise_for_status()
                    qr_data = res.json()
                    LOG.info(f"Nexu 响应: {qr_data}")

                    # 将 Nexu 的原始响应作为 answer 返回，由 Server 进一步解析
                    answer = json.dumps(qr_data)
                    response_type = "wechat-qr"

                    # 记录到历史（可选，或者只记录用户意图）
                    session.add_message("user", clean_content)
                    session.add_message("assistant", "[已生成微信连接二维码]")
            except Exception as e:
                LOG.error(f"调用 Nexu 接口失败: {e}")
                answer = "抱歉捏，openclaw服务暂时不可用，请稍后再试吧~"
                response_type = "chat"

        elif intent_result.type == IntentType.ANALYZE_SPEECH:
            # 仅仅识别出意图并把目标传回给 Server，不再主动去查库
            analyze_target = intent_result.answer or "请分析该用户的发言特点、性格或意图"
            answer = analyze_target
            response_type = "analyze-speech"
            # 存入到历史
            session.add_message("user", clean_content)
            session.add_message("assistant", f"[已转交发言分析请求] {analyze_target}")

        else:
            answer = intent_result.answer or "呜呜，我不太明白你的意思呢~"
            response_type = "chat"

        cost = round(time.time() - start_time, 2)
        LOG.info(f"回答耗时: {cost}s, type={response_type}")

        # 构建响应
        response = ChatResponse(type=response_type, answer=answer)

        if is_debug:
            response.debug = f"(aiCost: {cost}s, provider: {provider or 'openai'}, model: {model or 'gpt-5.2'})"

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
        reference_list = await search_client.search(search_query)
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

    async def analyze_speech(
            self,
            target: str,
            history_text: str,
            session_id: str = "",
            provider: Optional[str] = None,
            model: Optional[str] = None
    ) -> ChatResponse:
        """根据提供的历史记录生成发言分析报告"""
        start_time = time.time()
        LOG.info(f"开始生成发言分析报告, 目标: {target}, 历史记录长度: {len(history_text)}")

        from true_love_ai.llm.analyze_speech_prompt import get_analyze_system_prompt
        analyze_system_prompt = get_analyze_system_prompt(target, history_text)

        analyze_messages = [
            {"role": "system", "content": analyze_system_prompt},
            {"role": "user", "content": target}
        ]

        answer = await self.llm_router.chat(
            messages=analyze_messages,
            provider=provider,
            model=model
        )

        if session_id:
            session = self.session_manager.get_or_create(session_id)
            session.add_message("assistant", answer)

        cost = round(time.time() - start_time, 2)
        LOG.info(f"发言分析耗时: {cost}s")
        return ChatResponse(type="chat", answer=answer)
