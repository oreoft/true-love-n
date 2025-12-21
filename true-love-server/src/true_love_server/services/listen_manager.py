# -*- coding: utf-8 -*-
"""
Listen Manager - 监听管理器

负责微信监听的管理，通过 Base 的 /execute/* 接口操作底层 SDK。
所有连接管理逻辑集中在此模块，Base 端只提供底层能力。

职责：
- 本地管理 listen_chats.json（单一数据源）
- 通过 Base 的 execute 接口操作 SDK
- 提供监听状态查询、增删、刷新、重置等功能
"""

import logging
import time
from typing import Optional

from .listen_store import get_listen_store
from . import base_client

LOG = logging.getLogger("ListenManager")


class ListenManager:
    """
    监听管理器（单例）
    
    - 本地管理 listen_chats.json（单一数据源）
    - 通过 Base 的 execute 接口操作 SDK
    """

    _instance: Optional["ListenManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._store = get_listen_store()
        self._initialized = True
        LOG.info("ListenManager initialized")

    # ==================== 查询接口 ====================

    def get_listen_list(self) -> list[str]:
        """
        获取监听列表（从本地 JSON）
        
        Returns:
            监听对象名称列表
        """
        return self._store.list_all()

    def get_listener_status(self) -> dict:
        """
        获取监听状态
        
        通过 Base 的 execute 接口检查每个监听的健康状态。
        
        状态定义：
        - healthy: 子窗口存在 AND ChatInfo 能正确响应
        - unhealthy: 子窗口不存在 OR ChatInfo 无法响应
        
        Returns:
            状态结果，包含 listeners 和 summary
        """
        db_chats = self._store.list_all()

        if not db_chats:
            return {"listeners": [], "summary": {"healthy": 0, "unhealthy": 0}}

        # 通过 execute/wx 调用 GetAllSubWindow
        result = base_client.execute_wx("GetAllSubWindow", {})
        if not result.get("success"):
            LOG.error(f"GetAllSubWindow failed: {result.get('message')}")
            # 获取失败，所有标记为 unhealthy
            return {
                "listeners": [
                    {"chat": c, "status": "unhealthy", "reason": "get_windows_failed"}
                    for c in db_chats
                ],
                "summary": {"healthy": 0, "unhealthy": len(db_chats)}
            }

        # 解析窗口列表，提取窗口名称
        sub_windows = result.get("data", []) or []
        window_names = set()
        for w in sub_windows:
            # w 可能是 dict 或对象序列化后的结果
            who = w.get("who") if isinstance(w, dict) else None
            if who:
                window_names.add(who)

        LOG.debug(f"GetAllSubWindow returned {len(window_names)} windows: {window_names}")

        listeners = []
        summary = {"healthy": 0, "unhealthy": 0}

        for chat_name in db_chats:
            status_info = {"chat": chat_name, "status": None, "reason": None}

            # Step 1: 检查子窗口是否存在
            if chat_name not in window_names:
                status_info["status"] = "unhealthy"
                status_info["reason"] = "window_not_found"
                summary["unhealthy"] += 1
                listeners.append(status_info)
                continue

            # Step 2: 检查 ChatInfo 是否能响应
            chat_result = base_client.execute_chat(chat_name, "ChatInfo", {})
            if chat_result.get("success") and chat_result.get("data"):
                status_info["status"] = "healthy"
                summary["healthy"] += 1
            else:
                status_info["status"] = "unhealthy"
                status_info["reason"] = "chat_info_failed"
                summary["unhealthy"] += 1

            listeners.append(status_info)

        LOG.info(f"Listener status: {summary}")
        return {"listeners": listeners, "summary": summary}

    # ==================== 增删接口 ====================

    def add_listen(self, chat_name: str, skip_store: bool = False) -> dict:
        """
        添加监听
        
        流程：
        1. 切换 ChatWith（打开聊天窗口）
        2. 调用 Base 添加 SDK 监听
        3. 成功后写入本地 JSON（除非 skip_store=True）
        
        Args:
            chat_name: 聊天对象名称
            skip_store: 是否跳过本地存储操作（用于 reset 场景，已有记录无需重复写入）
            
        Returns:
            {"success": bool, "message": str}
        """
        # 检查是否已存在（仅在非 skip_store 模式下检查）
        if not skip_store and self._store.exists(chat_name):
            LOG.info(f"[{chat_name}] already in listen list")
            return {"success": True, "message": f"[{chat_name}] already exists"}

        # Step 1: 切换到聊天窗口
        chat_with_result = base_client.execute_wx("ChatWith", {"who": chat_name})
        if not chat_with_result.get("success"):
            LOG.error(f"ChatWith failed for [{chat_name}]: {chat_with_result.get('message')}")
            return {"success": False, "message": f"ChatWith failed: {chat_with_result.get('message')}"}

        # Step 2: 调用 Base 的 /listen/add 添加监听
        result = base_client.add_listen_chat(chat_name)

        if result.get("success"):
            # SDK 添加成功，写入本地（除非 skip_store）
            if not skip_store:
                self._store.add(chat_name)
            LOG.info(f"Added listener for [{chat_name}]")
            return {"success": True, "message": f"Added listener for [{chat_name}]"}
        else:
            LOG.error(f"Failed to add listener for [{chat_name}]: {result.get('message')}")
            return {"success": False, "message": result.get("message", "Unknown error")}

    def remove_listen(self, chat_name: str, skip_store: bool = False) -> dict:
        """
        移除监听
        
        流程：
        1. 调用 Base 移除 SDK 监听
        2. 从本地 JSON 删除（除非 skip_store=True）
        
        Args:
            chat_name: 聊天对象名称
            skip_store: 是否跳过本地存储操作（用于 reset 场景，不需要删除本地记录）
            
        Returns:
            {"success": bool, "message": str}
        """
        # 调用 Base 的 RemoveListenChat
        result = base_client.execute_wx("RemoveListenChat", {"nickname": chat_name})

        if result.get("success"):
            LOG.info(f"Removed listener for [{chat_name}]")
            if not skip_store:
                self._store.remove(chat_name)
            return {"success": True, "message": f"Removed listener for [{chat_name}]"}
        else:
            LOG.warning(f"SDK remove failed for [{chat_name}]: {result.get('message')}")
            if not skip_store:
                self._store.remove(chat_name)
            return {"success": True, "message": f"Removed from local (SDK: {result.get('message', 'failed')})"}

    # ==================== 刷新/重置接口 ====================

    def refresh_listen(self) -> dict:
        """
        智能刷新监听
        
        流程：
        1. 获取监听状态
        2. healthy 的跳过，unhealthy 的执行 reset
        
        Returns:
            刷新结果
        """
        status = self.get_listener_status()
        listeners = status.get("listeners", [])

        if not listeners:
            return {
                "total": 0,
                "success_count": 0,
                "fail_count": 0,
                "listeners": []
            }

        result_listeners = []
        success_count = 0
        fail_count = 0

        for item in listeners:
            chat_name = item["chat"]
            before_status = item["status"]

            listener_info = {
                "chat": chat_name,
                "before": before_status,
                "action": None,
                "after": None,
                "success": None
            }

            if before_status == "healthy":
                # 健康的不处理
                listener_info["action"] = "skip"
                listener_info["after"] = "healthy"
                listener_info["success"] = True
                success_count += 1
            else:
                # unhealthy: 执行 reset
                listener_info["action"] = "reset"
                reset_result = self.reset_listener(chat_name)
                success = reset_result.get("success", False)
                listener_info["success"] = success
                listener_info["after"] = "healthy" if success else "unhealthy"
                if success:
                    success_count += 1
                    LOG.info(f"Reset listener for [{chat_name}] succeeded")
                else:
                    fail_count += 1
                    LOG.error(f"Reset listener for [{chat_name}] failed: {reset_result.get('message')}")

            result_listeners.append(listener_info)

        return {
            "total": len(result_listeners),
            "success_count": success_count,
            "fail_count": fail_count,
            "listeners": result_listeners
        }

    def reset_listener(self, chat_name: str) -> dict:
        """
        重置单个监听
        
        流程：
        1. 切换到 SwitchToChat
        2. 关闭子窗口
        3. 调用 remove_listen (skip_store=True)
        4. 等待 UI 稳定
        5. 调用 add_listen (skip_store=True)
        
        Args:
            chat_name: 聊天对象名称
            
        Returns:
            {"success": bool, "message": str, "steps": list}
        """
        if not self._store.exists(chat_name):
            return {"success": False, "message": f"Chat [{chat_name}] not in local config", "steps": []}

        steps = []

        # Step 1: 切换到聊天页面
        try:
            result = base_client.execute_wx("SwitchToChat", {})
            steps.append({"step": "switch_to_chat", "success": result.get("success", False)})
        except Exception as e:
            steps.append({"step": "switch_to_chat", "success": False, "error": str(e)})

        # Step 2: 尝试关闭子窗口（幂等操作）
        try:
            result = base_client.execute_chat(chat_name, "Close", {})
            steps.append({"step": "close_window", "success": result.get("success", False)})
        except Exception as e:
            steps.append({"step": "close_window", "success": False, "error": str(e)})

        # Step 3: 移除监听（skip_store=True，不删除本地记录）
        try:
            result = self.remove_listen(chat_name, skip_store=True)
            steps.append({"step": "remove_listen", "success": result.get("success", False)})
        except Exception as e:
            steps.append({"step": "remove_listen", "success": False, "error": str(e)})

        # Step 4: 等待 UI 稳定
        time.sleep(0.5)
        steps.append({"step": "wait", "success": True, "duration": 0.5})

        # Step 5: 重新添加监听（skip_store=True，不重复写入本地记录）
        try:
            result = self.add_listen(chat_name, skip_store=True)
            steps.append({"step": "add_listen", "success": result.get("success", False)})

            if result.get("success"):
                LOG.info(f"Reset listener for [{chat_name}] succeeded")
                return {"success": True, "message": f"Reset listener for [{chat_name}]", "steps": steps}
            else:
                LOG.error(f"Failed to re-add listener for [{chat_name}]: {result.get('message')}")
                return {"success": False, "message": f"Failed to re-add listener: {result.get('message')}",
                        "steps": steps}
        except Exception as e:
            steps.append({"step": "add_listen", "success": False, "error": str(e)})
            LOG.error(f"Exception re-adding listener for [{chat_name}]: {e}")
            return {"success": False, "message": str(e), "steps": steps}

    def reset_all_listeners(self) -> dict:
        """
        重置所有监听
        
        流程：
        1. 把所有子窗口都关掉
        2. 切换页面刷新 UI（联系人和对话来回切一下）
        3. 挨个调用 reset_listener（虽然里面也会关闭子窗口，但是没关系，幂等的）
        
        Returns:
            {"success": bool, "message": str, "total": int, "recovered": list, "failed": list, "steps": list}
        """
        db_chats = self._store.list_all()

        if not db_chats:
            return {
                "success": True,
                "message": "No listeners in config",
                "total": 0,
                "recovered": [],
                "failed": [],
                "steps": []
            }

        steps = []
        recovered = []
        failed = []

        LOG.info(f"Starting reset all listeners, total: {len(db_chats)}")

        # Step 1: 关闭所有子窗口
        closed_count = 0
        try:
            result = base_client.execute_wx("GetAllSubWindow", {})
            if result.get("success"):
                sub_windows = result.get("data", []) or []
                for w in sub_windows:
                    who = w.get("who") if isinstance(w, dict) else None
                    if who:
                        close_result = base_client.execute_chat(who, "Close", {})
                        if close_result.get("success"):
                            closed_count += 1
            steps.append({"step": "close_all_windows", "success": True, "closed": closed_count})
            LOG.info(f"Closed {closed_count} sub windows")
        except Exception as e:
            steps.append({"step": "close_all_windows", "success": False, "error": str(e)})
            LOG.warning(f"Failed to close sub windows: {e}")

        # Step 2: 切换页面刷新 UI（联系人和对话来回切一下）
        try:
            base_client.execute_wx("SwitchToContact", {})
            time.sleep(0.3)
            base_client.execute_wx("SwitchToChat", {})
            time.sleep(0.3)
            steps.append({"step": "switch_pages", "success": True})
            LOG.info("Switched pages to refresh UI")
        except Exception as e:
            steps.append({"step": "switch_pages", "success": False, "error": str(e)})
            LOG.warning(f"Failed to switch pages: {e}")

        # Step 3: 挨个调用 reset_listener（幂等操作）
        for chat_name in db_chats:
            try:
                result = self.reset_listener(chat_name)
                if result.get("success"):
                    recovered.append(chat_name)
                    LOG.info(f"Reset listener for [{chat_name}] succeeded")
                else:
                    failed.append(chat_name)
                    LOG.error(f"Reset listener for [{chat_name}] failed: {result.get('message')}")
            except Exception as e:
                failed.append(chat_name)
                LOG.error(f"Exception resetting listener for [{chat_name}]: {e}")

        steps.append({
            "step": "reset_listeners",
            "success": len(failed) == 0,
            "recovered": len(recovered),
            "failed": len(failed)
        })

        success = len(failed) == 0
        message = f"Reset complete: {len(recovered)}/{len(db_chats)} recovered"
        if failed:
            message += f", {len(failed)} failed"

        LOG.info(message)

        return {
            "success": success,
            "message": message,
            "total": len(db_chats),
            "recovered": recovered,
            "failed": failed,
            "steps": steps
        }


# 全局单例获取函数
def get_listen_manager() -> ListenManager:
    """获取 ListenManager 单例"""
    return ListenManager()
