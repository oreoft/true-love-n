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
        max_history: int = 50,
        ttl_seconds: int = 86400
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
    
    @staticmethod
    def get_current_time_context() -> str:
        """获取当前时间上下文（供各模块复用）"""
        now = datetime.now()
        return (
            f"当前时间: {now.strftime('%Y年%m月%d日 %H:%M')}，"
            f"当前年份: {now.year}年"
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
        
        # 时间与能力提示
        time_hint = (
            f"{self.get_current_time_context()}。"
            f"你已接入搜索引擎，可以获取实时信息。"
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
        system_prompt: Optional[str] = None
    ) -> Session:
        """获取或创建会话"""
        with self._lock:
            # 清理过期会话
            self._cleanup_expired()
            
            if session_id not in self._sessions:
                # 根据用户选择 prompt（prompt2_users 用户使用 prompt2）
                if system_prompt is None:
                    system_prompt = (
                        self.prompt2 
                        if session_id in self.prompt2_users 
                        else self.default_prompt
                    )
                
                self._sessions[session_id] = Session(
                    session_id=session_id,
                    system_prompt=system_prompt,
                    max_history=self.max_history,
                    ttl_seconds=self.ttl_seconds
                )
                LOG.debug(f"创建新会话: {session_id}")
            
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
