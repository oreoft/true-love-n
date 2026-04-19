# -*- coding: utf-8 -*-
"""
聊天服务模块（精简版）

意图识别已废弃，消息处理由 AgentLoop 负责。
本模块保留以下功能：
  - analyze_speech:       生成发言分析报告（供 /get-analyze-speech API 使用）
  - extract_memory_facts: 从分析报告中提取结构化记忆（供 /extract-memory API 和 analyze_speech_skill 使用）
"""
import json
import logging
from typing import Optional

from true_love_ai.core.config import get_config
from true_love_ai.core.session import get_session_manager
from true_love_ai.llm.router import get_llm_router
from true_love_ai.models.response import ChatResponse

LOG = logging.getLogger(__name__)


class ChatService:

    def __init__(self):
        self.config = get_config()
        self.session_manager = get_session_manager()
        self.llm_router = get_llm_router()

    async def analyze_speech(
            self,
            history_text: str,
            session_id: str = "",
            metadata: dict = None,
            provider: Optional[str] = None,
            model: Optional[str] = None
    ) -> ChatResponse:
        """根据提供的历史记录生成发言分析报告"""
        import time
        start_time = time.time()
        metadata = metadata or {}
        target = metadata.get("target", "分析该用户的发言特点、性格或意图")
        LOG.info(f"开始生成发言分析报告, session_id={session_id}, metadata={metadata}")

        from true_love_ai.llm.analyze_speech_prompt import get_analyze_system_prompt
        analyze_system_prompt = get_analyze_system_prompt(history_text, metadata)

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

        LOG.info("发言分析耗时: %.2fs", round(time.time() - start_time, 2))
        return ChatResponse(type="chat", answer=answer)

    async def extract_memory_facts(self, text: str, sender: str) -> list[dict]:
        """
        从发言分析报告中提取结构化用户事实，供 server 写入记忆库。

        Returns:
            [{key, value}] 列表，异常时返回空列表。
        """
        extract_prompt = (
            f"请从下面这段关于用户「{sender}」的分析报告中，提取关键个人事实。\n"
            "以 JSON 数组格式返回，每项包含 key 和 value 两个字段。\n"
            "key 只能是以下之一：personality（性格）/ occupation（职业）/ preference（爱好偏好）/ fact（其他事实）/ timezone（所在时区）\n"
            "要求：\n"
            "1. 只提取确定性较高的信息，不要猜测，不超过 8 条。\n"
            "2. 除了 timezone 外，其他 value 用中文简洁描述。\n"
            "3. 如果提取到了 timezone，其 value 【必须】转换为标准的 IANA 时区名称（格式为 Region/City，例如 America/New_York, Asia/Shanghai, Europe/London 等）。如果用户描述的是简称（如\"美中时区\"、\"PST\"等），请自行推导换算为其代表性的 IANA 标准城市名称。绝对不要输出 UTC-5 或中文。\n"
            "只返回 JSON 数组，不要其他文字。\n\n"
            f"分析报告：\n{text}"
        )

        try:
            raw = await self.llm_router.chat(
                messages=[{"role": "user", "content": extract_prompt}],
            )
            raw = raw.strip()
            if raw.startswith("```"):
                raw = "\n".join(raw.split("\n")[1:])
            if raw.endswith("```"):
                raw = raw[: raw.rfind("```")]

            facts = json.loads(raw.strip())
            if not isinstance(facts, list):
                raise ValueError(f"期望 list，实际: {type(facts)}")

            allowed = {"personality", "occupation", "preference", "fact", "timezone"}
            facts = [f for f in facts if isinstance(f, dict) and f.get("key") in allowed and f.get("value")]
            LOG.info("extract_memory_facts: sender=%s, 提取到 %d 条", sender, len(facts))
            return facts
        except Exception as e:
            LOG.warning("extract_memory_facts 失败，返回空列表: %s", e)
            return []
