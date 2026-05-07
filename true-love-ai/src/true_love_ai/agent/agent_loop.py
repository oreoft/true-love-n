# -*- coding: utf-8 -*-
"""
Agent Loop

核心 Agent 执行引擎：接收消息 → 构建上下文 → LLM + tools 循环 → 发送回复

流程：
    收到 msg
      → 从 AI 本地 DB 获取 user_ctx
      → 获取 session history
      → build prompt
      → LLM (带 tools)
      → if tool_calls: 执行 skill → append 结果 → 继续循环
      → if text answer: 通过 Server /action/send 发送 → 保存 session
"""

import asyncio
import json
import logging
import re
from typing import Optional

from true_love_ai.core.session import get_session_manager
from true_love_ai.llm.router import get_llm_router
from true_love_ai.memory.memory_manager import get_user_context
from true_love_ai.agent import skill_registry

LOG = logging.getLogger("AgentLoop")

# 单次会话最大 tool 调用轮次（防止死循环）
MAX_TOOL_ITERATIONS = 6
# 单个 skill 执行超时（秒）
SKILL_TIMEOUT_SECONDS = 120

# 触发词清理
_TRIGGER_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [r"@真爱粉\s*", r"\bzaf\b"]]


def _clean_content(content: str) -> str:
    for pat in _TRIGGER_PATTERNS:
        content = pat.sub("", content)
    return content.strip()


class AgentLoop:
    """Agent 执行引擎（单例使用）"""

    def __init__(self):
        self.llm_router = get_llm_router()
        self.session_manager = get_session_manager()

    async def run(self, msg: dict) -> None:
        """
        处理一条消息（完整 agent loop）。

        Args:
            msg: ChatMsg.to_dict() 格式的字典
        """
        platform = msg.get("platform", "wechat")
        sender_id = msg.get("sender_id", "")
        sender_name = msg.get("sender_name", "") or sender_id
        chat_id = msg.get("chat_id", "")
        is_group = msg.get("is_group", False)
        msg_type = msg.get("msg_type", "text")

        # session key 加 platform 前缀，天然隔离多平台
        _session_base = chat_id if is_group else sender_id
        session_id = f"{platform}:{_session_base}"
        at_user = sender_id if is_group else ""
        receiver = chat_id if is_group else sender_id

        LOG.info("AgentLoop.run: platform=%s sender_id=%s sender_name=%s session=%s type=%s",
                 platform, sender_id, sender_name, session_id, msg_type)

        # 构建用户侧消息内容
        user_content = self._build_user_content(msg)
        if not user_content:
            LOG.warning("无法解析消息内容，跳过: type=%s", msg_type)
            await self._send_reply(receiver, "抱歉，这种消息我暂时还不太看得懂呢~", at_user)
            return

        # 获取用户画像并注入 session
        user_ctx = get_user_context(session_id, sender_id)
        session = self.session_manager.get_or_create(session_id, user_ctx=user_ctx)
        session.add_message("user", user_content)

        # 获取当前可用 tools
        tools = skill_registry.get_all_tool_schemas()

        # 开始 Agent Loop
        messages = session.get_messages_for_llm()
        reply = None

        for iteration in range(MAX_TOOL_ITERATIONS):
            try:
                result_type, result = await self.llm_router.chat_for_agent(
                    messages=messages,
                    tools=tools,
                )
            except Exception as e:
                LOG.exception("LLM 调用失败 (iteration=%d): %s", iteration, e)
                reply = "呜呜~出了点小状况，稍后再试试吧~"
                break

            if result_type == "text":
                reply = result
                break

            # result_type == "tool_calls"
            tool_calls = result
            LOG.info("LLM 请求执行 %d 个 tool (iteration=%d)", len(tool_calls), iteration)

            # 1. 把 assistant 的 tool_calls 消息追加到 messages
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"], ensure_ascii=False),
                        },
                    }
                    for tc in tool_calls
                ],
            })

            # 2. 并行执行所有 tool，把结果追加到 messages
            tool_results = await asyncio.gather(*[
                self._execute_tool(tc, session_id, sender_id, sender_name, is_group, receiver, at_user)
                for tc in tool_calls
            ])
            for tc, tool_result in zip(tool_calls, tool_results):
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": tool_result,
                })
        else:
            # 超出最大轮次
            LOG.warning("AgentLoop 超过最大迭代次数 (%d)", MAX_TOOL_ITERATIONS)
            reply = "处理超时了，稍后再试试吧~"

        if reply:
            session.add_message("assistant", reply)
            await self._send_reply(receiver, reply, at_user, platform=platform)

    def _build_user_content(self, msg: dict) -> Optional[str]:
        """把各类消息类型转换为 LLM 可理解的文本"""
        msg_type = msg.get("msg_type", "text")
        content = _clean_content(msg.get("content", ""))

        if msg_type == "text":
            # 检查是否含链接，若有则附上链接内容
            url = self._extract_first_link(content)
            if url:
                crawled = self._crawl_content(url)
                if crawled:
                    return f"{content}\n\n[链接内容]\n{crawled}"
            return content or None

        if msg_type == "voice":
            voice_msg = msg.get("voice_msg") or {}
            text = voice_msg.get("text_content", "")
            return f"[语音转文字]: {text}" if text else None

        if msg_type == "image":
            image_msg = msg.get("image_msg") or {}
            file_path = image_msg.get("file_path", "")
            desc = content or "请分析这张图片"
            if file_path:
                return f"[图片:{file_path}] {desc}"
            return desc

        if msg_type == "link":
            link_msg = msg.get("link_msg") or {}
            url = link_msg.get("url", "")
            if url:
                crawled = self._crawl_content(url)
                desc = content or "请分析这个链接"
                return f"{desc}\n\n[链接内容]\n{crawled}" if crawled else f"{desc} {url}"
            return content or None

        if msg_type == "file":
            file_msg = msg.get("file_msg") or {}
            file_path = file_msg.get("file_path", "")
            if file_path:
                desc = content or "请分析这个文件"
                return f"[文件:{file_path}] {desc}"
            return content or None

        if msg_type == "video":
            return f"[视频消息] {content}" if content else "[视频消息]"

        quoted = msg.get("refer_msg")
        if quoted:
            q_type = quoted.get("msg_type", "")
            q_content = quoted.get("content", "")

            def _get_ref(sub_key: str) -> str:
                sub = quoted.get(sub_key) or {}
                # 新格式：resource.ref；旧格式：file_path
                resource = sub.get("resource") or {}
                return resource.get("ref") or sub.get("file_path", "")

            if q_type == "image":
                ref = _get_ref("image_msg")
                suffix = f"[引用图片:{ref}]" if ref else "[引用图片]"
            elif q_type == "video":
                ref = _get_ref("video_msg")
                suffix = f"[引用视频:{ref}]" if ref else "[引用视频]"
            elif q_type == "file":
                ref = _get_ref("file_msg")
                suffix = f"[引用文件:{ref}]" if ref else "[引用文件]"
            else:
                suffix = f"[引用{q_type}内容]: {q_content}"
            return f"{content}\n\n{suffix}" if content else suffix

        return content or None

    async def _execute_tool(
            self,
            tool_call: dict,
            session_id: str,
            sender_id: str,
            sender_name: str,
            is_group: bool,
            receiver: str,
            at_user: str,
    ) -> str:
        """执行单个 tool，返回结果字符串"""
        name = tool_call["name"]
        args = tool_call["arguments"]
        LOG.info("执行 tool: %s, args=%s", name, str(args)[:200])

        ctx = {
            "session_id": session_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "is_group": is_group,
            "receiver": receiver,
            "at_user": at_user,
        }

        try:
            notify_msg = skill_registry.get_notify(name)
            if notify_msg:
                import random
                from true_love_ai.agent.server_client import send_text
                msg = random.choice(notify_msg) if isinstance(notify_msg, list) else notify_msg
                await send_text(receiver, msg, at_user)

            result = await asyncio.wait_for(
                skill_registry.execute(name, args, ctx),
                timeout=SKILL_TIMEOUT_SECONDS,
            )
            LOG.info("tool %s 执行结果: %s", name, str(result)[:200])
            return str(result)
        except asyncio.TimeoutError:
            LOG.error("tool %s 执行超时 (%ds)", name, SKILL_TIMEOUT_SECONDS)
            return f"[执行超时] 技能 {name} 处理时间过长，请稍后重试"
        except Exception as e:
            from true_love_ai.agent.skills.permission import PermissionDenied
            if isinstance(e, PermissionDenied):
                return str(e)
            LOG.exception("tool %s 执行异常: %s", name, e)
            return f"[执行失败] {e}"

    async def _send_reply(self, receiver: str, content: str, at_user: str,
                          platform: str = "wechat") -> None:
        """通过 Server 发送最终回复"""
        from true_love_ai.agent.server_client import send_text
        try:
            ok = await send_text(receiver, content, at_user, platform=platform)
            if not ok:
                LOG.error("发送回复失败: receiver=%s platform=%s", receiver, platform)
        except Exception as e:
            LOG.exception("发送回复异常: %s", e)

    @staticmethod
    def _extract_first_link(text: str) -> Optional[str]:
        match = re.search(r"https?://[^\s]+", text)
        return match.group() if match else None

    @staticmethod
    def _crawl_content(url: str) -> str:
        if not url:
            return ""
        try:
            import httpx
            request_url = "https://www.textise.net/showtext.aspx?strURL=" + url
            headers = {"User-Agent": "PostmanRuntime/7.40.0"}
            with httpx.Client(timeout=30) as client:
                response = client.get(request_url, headers=headers)
            content = response.text
            content = re.sub(r"\(http.*?\)", "", content)
            return content.replace("[]", "").replace("\n\n", "\n").strip()[:3000]
        except Exception:
            return ""


# 全局单例
_agent_loop: Optional[AgentLoop] = None


def get_agent_loop() -> AgentLoop:
    global _agent_loop
    if _agent_loop is None:
        _agent_loop = AgentLoop()
    return _agent_loop
