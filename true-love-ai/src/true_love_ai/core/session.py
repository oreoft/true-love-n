#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话管理模块
简单的内存存储 + TTL 过期机制
"""
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional

from true_love_ai.core.config import get_config

LOG = logging.getLogger(__name__)


class Session:
    """单个会话"""
    
    def __init__(
        self,
        session_id: str,
        system_prompt: str,
        max_history: int = 100,
        ttl_seconds: int = 864000
    ):
        self.session_id = session_id
        self.system_prompt = system_prompt
        self.max_history = max_history
        self.ttl = timedelta(seconds=ttl_seconds)
        
        self.messages: list[dict] = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    @property
    def is_expired(self) -> bool:
        """检查会话是否过期"""
        return datetime.now() > self.updated_at + self.ttl
    
    def add_message(self, role: str, content: str):
        """添加消息"""
        self.messages.append({
            "role": role,
            "content": content
        })
        self.updated_at = datetime.now()
        
        # 滚动清除超出限制的消息
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]
    
    def get_current_time_context(self) -> str:
        """获取当前时间上下文（带时区感知）"""
        import re
        from datetime import datetime, timezone
        from zoneinfo import ZoneInfo
        
        tz_str = "Asia/Shanghai"  # default
        if self.system_prompt:
            # 去提取 user_ctx 中的 时区: America/New_York 
            # 放宽正则以兼容旧的异常记录，提取直到空格或 | 符号
            match = re.search(r"时区[：:]\s*([^\s\|]+)", self.system_prompt)
            if match:
                tz_str = match.group(1).strip()
                
        try:
            tz = ZoneInfo(tz_str)
        except Exception:
            # 如果解析失败，回退到国内默认时区，避免崩溃
            tz_str = "Asia/Shanghai"
            tz = ZoneInfo(tz_str)
            
        now_utc = datetime.now(timezone.utc)
        now_local = now_utc.astimezone(tz)
        
        return (
            f"系统当前世界标准时间(UTC): {now_utc.strftime('%Y-%m-%d %H:%M:%S')}。\n"
            f"该用户当前当地时间(时区={tz_str}): {now_local.strftime('%Y-%m-%d %H:%M:%S')}。\n"
            f"【极其重要】：如果用户要求你进行「x分钟后」、「明天几点」等时间推算，请**直接以系统告诉你的【该用户当地时间】为起点**进行相加减。\n"
            f"计算出的结果绝对不要再额外进行时差加减偏移！最后务必将你的结果转化为标准 ISO-8601 带时区的格式输出（例如：2026-04-13T10:30:00-05:00）。"
        )
    
    def get_messages_for_llm(self) -> list[dict]:
        """获取用于 LLM 最终回答的消息列表"""
        messages = []
        
        # 系统 prompt
        if self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })
        
        # 获取可用技能列表注入到 prompt，让 AI 知道自己能干嘛
        from true_love_ai.skills import get_skill_schemas
        skills = get_skill_schemas()
        skill_desc_list = [f"- {s['function']['name']}: {s['function']['description']}" for s in skills]
        skill_text = "\n".join(skill_desc_list)
        
        # 时间与能力提示
        time_hint = (
            f"{self.get_current_time_context()}\n"
            f"你已接入多模态 Agent 系统，能够执行特定的技能任务。\n"
            f"如果你想知道你具备哪些拓展技能能力，以下是当前加载的专属技能列表：\n{skill_text}\n"
        )
        messages.append({
            "role": "system",
            "content": time_hint
        })
        
        # 对话历史
        messages.extend(self.messages)
        
        return messages
    
    def get_context_for_intent(self, current_content: str, max_turns: int = 4) -> list[dict]:
        """
        获取用于意图识别的上下文消息
        
        Args:
            current_content: 当前用户消息
            max_turns: 最大历史轮数（一轮 = user + assistant）
            
        Returns:
            用于意图识别的消息列表
        """
        messages = []
        
        # 系统 prompt（角色设定等）
        if self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })
        
        # 时间信息
        messages.append({
            "role": "system", 
            "content": self.get_current_time_context()
        })
        
        # 强制技能调用的环境提示
        from true_love_ai.skills import get_skill_schemas
        skills = get_skill_schemas()
        skill_desc_list = [f"- {s['function']['name']}: {s['function']['description']}" for s in skills]
        skill_text = "\n".join(skill_desc_list)
        
        intent_system_prompt = (
            "【系统最高级别警告】：如果用户在陈述自己的长期客观事实（例如：他在哪个时区、性格、爱好、职业、禁忌等），"
            "或明确要求你记住关于他的某件事时，**你绝对不能**仅使用普通的语言回复（即不能只返回 type_answer 说你记住了）！\n"
            "你必须且只能立刻使用相应的保存技能（如 save_user_profile）来将此信息入库持久化！如果你不调用该技能，数据将永远丢失！\n"
            f"当你需要保存或者操作时，请从以下技能列表中选择：\n{skill_text}\n"
        )
        messages.append({
            "role": "system",
            "content": intent_system_prompt
        })
        
        # 添加最近的对话历史
        if self.messages:
            recent_messages = self.messages[-(max_turns * 2):]
            messages.extend(recent_messages)
        
        # 当前用户消息
        messages.append({"role": "user", "content": current_content})
        
        return messages
    
    def clear(self):
        """清空消息"""
        self.messages = []
        self.updated_at = datetime.now()


class SessionManager:
    """
    会话管理器
    线程安全的内存存储
    """
    
    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()
        
        config = get_config()
        self.max_history = config.session.max_history
        self.ttl_seconds = config.session.ttl_seconds
        self.default_prompt = config.chatgpt.prompt if config.chatgpt else ""
        self.prompt2 = config.chatgpt.prompt2 if config.chatgpt else ""
        self.prompt2_users = config.chatgpt.prompt2_users if config.chatgpt else []
    
    def get_or_create(
        self,
        session_id: str,
        system_prompt: Optional[str] = None,
        user_ctx: Optional[str] = None,
    ) -> Session:
        """获取或创建会话

        Args:
            session_id:    会话 ID
            system_prompt: 覆盖默认 system prompt（可选）
            user_ctx:      用户画像文本，有值时追加到 system prompt 末尾
        """
        with self._lock:
            # 清理过期会话
            self._cleanup_expired()

            # 根据 user_ctx 构建完整 system prompt
            def _build_prompt(base: str) -> str:
                if user_ctx:
                    return f"{base}\n\n## 关于发送者的已知信息\n{user_ctx}"
                return base

            if session_id not in self._sessions:
                # 根据用户选择 prompt（prompt2_users 用户使用 prompt2）
                if system_prompt is None:
                    base_prompt = (
                        self.prompt2
                        if session_id in self.prompt2_users
                        else self.default_prompt
                    )
                else:
                    base_prompt = system_prompt

                self._sessions[session_id] = Session(
                    session_id=session_id,
                    system_prompt=_build_prompt(base_prompt),
                    max_history=self.max_history,
                    ttl_seconds=self.ttl_seconds
                )
                LOG.debug(f"创建新会话: {session_id}, has_user_ctx={bool(user_ctx)}")
            else:
                # 会话已存在：若 user_ctx 有值则刷新 system prompt（记忆可能更新了）
                if user_ctx:
                    session = self._sessions[session_id]
                    base_prompt = (
                        self.prompt2
                        if session_id in self.prompt2_users
                        else self.default_prompt
                    )
                    session.system_prompt = _build_prompt(base_prompt)

            return self._sessions[session_id]
    
    def get(self, session_id: str) -> Optional[Session]:
        """获取会话（不创建）"""
        with self._lock:
            session = self._sessions.get(session_id)
            if session and session.is_expired:
                del self._sessions[session_id]
                return None
            return session
    
    def delete(self, session_id: str):
        """删除会话"""
        with self._lock:
            self._sessions.pop(session_id, None)
    
    def _cleanup_expired(self):
        """清理过期会话"""
        expired = [
            sid for sid, session in self._sessions.items()
            if session.is_expired
        ]
        for sid in expired:
            del self._sessions[sid]
            LOG.debug(f"清理过期会话: {sid}")
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        with self._lock:
            return {
                "total_sessions": len(self._sessions),
                "sessions": [
                    {
                        "id": sid,
                        "message_count": len(s.messages),
                        "created_at": s.created_at.isoformat(),
                        "updated_at": s.updated_at.isoformat()
                    }
                    for sid, s in self._sessions.items()
                ]
            }


# 全局会话管理器实例
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """获取会话管理器单例"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
