# -*- coding: utf-8 -*-
"""
WxAuto Adapter - wxautox4 SDK 适配器

实现 WeChatClientProtocol 接口，封装 wxautox4 的具体调用。
"""

import json
import logging
import time
from typing import Optional

# This is a special import, please do not modify
from true_love_base.wxautox4x.wxautox4x import WeChat
from wxautox4.param import WxParam

from true_love_base.core.client_protocol import WeChatClientProtocol, MessageCallback
from true_love_base.adapters.message_converter import convert_message
from true_love_base.utils.path_resolver import get_wx_imgs_dir

LOG = logging.getLogger("WxAutoAdapter")

# 设置 wxauto 默认文件保存路径到 server 的 wx_imgs 目录
_wx_imgs_dir = get_wx_imgs_dir()
if _wx_imgs_dir:
    WxParam.DEFAULT_SAVE_PATH = _wx_imgs_dir
    LOG.info(f"Set WxParam.DEFAULT_SAVE_PATH to: {_wx_imgs_dir}")


class WxAutoClient(WeChatClientProtocol):
    """
    wxautox4 客户端适配器
    
    实现 WeChatClientProtocol 接口，封装 wxautox4 的所有操作。
    """

    def __init__(self):
        """初始化 wxautox4 客户端"""
        self._wx = None
        self._running = False
        self._listeners: dict[str, MessageCallback] = {}
        self._self_name: Optional[str] = None

        self._init_client()

    def _init_client(self):
        """初始化 wxautox4 WeChat 实例"""
        try:
            self._wx = WeChat()
            self._running = True
            LOG.info("WxAutoClient initialized successfully")
        except Exception as e:
            LOG.error(f"Failed to initialize WxAutoClient: {e}")
            raise RuntimeError(f"Failed to initialize wxautox4: {e}")

    @property
    def wx(self):
        """获取底层 WeChat 实例"""
        if self._wx is None:
            raise RuntimeError("WeChat client not initialized")
        return self._wx

    # ==================== 通用方法 ====================

    def _check_response(self, result, action: str, target: str) -> bool:
        """
        检查 WxResponse 结果
        
        Args:
            result: WxResponse 类型的返回值
            action: 操作名称，用于日志
            target: 操作目标，用于日志
            
        Returns:
            bool: 操作是否成功
        """
        if result:
            LOG.info(f"[{action}] [{target}] succeeded")
            return True
        else:
            # WxResponse 失败时，通过 result['message'] 获取错误信息
            error_msg = result.get('message', 'Unknown error') if isinstance(result, dict) else str(result)
            LOG.error(f"[{action}] [{target}] failed: {error_msg}")
            return False

    # ==================== 账号信息 ====================

    def get_self_id(self) -> str:
        """获取当前登录账号ID（wxautox4 可能不支持，返回昵称）"""
        return self.get_self_name()

    def get_self_name(self) -> str:
        """获取当前登录账号昵称"""
        if self._self_name is None:
            try:
                # wxautox4 获取昵称的方式
                self._self_name = getattr(self.wx, 'nickname', None) or "Unknown"
            except Exception as e:
                LOG.warning(f"Failed to get self name: {e}")
                self._self_name = "Unknown"
        return self._self_name

    @staticmethod
    def _dump_obj_attrs(obj) -> str:
        """
        获取对象的所有公开属性（非方法、非私有），返回格式化的 JSON 字符串
        
        Args:
            obj: 要打印的对象
            
        Returns:
            格式化的属性字符串
        """
        result = {}
        for attr in dir(obj):
            if attr.startswith('_'):
                continue
            try:
                value = getattr(obj, attr)
                if not callable(value):
                    # 尝试转为可序列化的类型
                    try:
                        json.dumps(value, ensure_ascii=False)
                        result[attr] = value
                    except (TypeError, ValueError):
                        result[attr] = repr(value)
            except Exception:
                pass
        return json.dumps(result, ensure_ascii=False, indent=2)

    # ==================== 消息发送 ====================

    def send_text(self, receiver: str, content: str, at_list: Optional[list[str]] = None) -> bool:
        """发送文本消息"""
        try:
            # 构建@内容
            if at_list:
                at_str = " ".join([f"@{name}" for name in at_list])
                content = f"{at_str}\n{content}"

            result = self.wx.SendMsg(content, receiver)
            LOG.debug(f"SendMsg content: {content[:50]}...")
            return self._check_response(result, "SendMsg", receiver)
        except Exception as e:
            LOG.error(f"Failed to send text to [{receiver}]: {e}")
            return False

    def send_image(self, receiver: str, image_path: str) -> bool:
        """发送图片"""
        try:
            result = self.wx.SendFiles(image_path, receiver)
            LOG.debug(f"SendFiles(image) path: {image_path}")
            return self._check_response(result, "SendFiles(image)", receiver)
        except Exception as e:
            LOG.error(f"Failed to send image to [{receiver}]: {e}")
            return False

    def send_file(self, receiver: str, file_path: str) -> bool:
        """发送文件"""
        try:
            result = self.wx.SendFiles(file_path, receiver)
            LOG.debug(f"SendFiles path: {file_path}")
            return self._check_response(result, "SendFiles", receiver)
        except Exception as e:
            LOG.error(f"Failed to send file to [{receiver}]: {e}")
            return False

    # ==================== 消息监听 ====================

    def _create_internal_callback(self, chat_name: str, callback: MessageCallback):
        """
        创建内部回调函数
        
        将用户回调包装成 wxauto 需要的内部回调格式，包含消息过滤和格式转换逻辑。
        
        Args:
            chat_name: 聊天对象名称
            callback: 用户回调函数
            
        Returns:
            内部回调函数（签名为 (raw_msg, chat)）
            
        Note:
            wxauto 回调签名是 (msg, chat)，必须接收两个参数
            
            示例 raw_msg 属性：
            私聊
             {
                "attr": "friend", # 获取 attr, 属性system：系统消息 self：自己发送的消息 friend：好友消息 other：其他消息
                "chat_info": {
                    "chat_type": "friend",
                    "chat_name": "纯路人"
                    },
                "content": "hello",
                "control": "<wxautox4.uia.uiautomation.ListItemControl object at 0x0000023CA83F92B0>",
                "hash": "0c6a86758fe737c7d0c3a9fd28474bb0",
                "hash_text": "(56,360)hello",
                "id": "cd886a97fd1c05f6d49f628d6c114d16",
                "parent": "<wxautox4.ui.chatbox.ChatBox object at 0x0000023CA8BCB200>",
                "root": "<wxautox4 - WeChatSubWnd object(\"纯路人\")>",
                "sender": "纯路人",
                "type": "text" # https://plus.wxauto.org/docs/class/Message.html
             }
             群消息
             {
                  "attr": "friend",
                  "chat_info": {
                    "chat_type": "group",
                    "chat_name": "委员会",
                    "group_member_count": 6
                  },
                  "content": "@真爱粉",
                  "control": "<wxautox4.uia.uiautomation.ListItemControl object at 0x0000023CA8BD8CE0>",
                  "hash": "27913b5c034854e5a4d2268fd0e380d0",
                  "hash_text": "(77,360)@真爱粉",
                  "id": "2e8a2aff7f368555d9cc5bd317acc532",
                  "parent": "<wxautox4.ui.chatbox.ChatBox object at 0x0000023CA8BD8560>",
                  "root": "<wxautox4 - WeChatSubWnd object(\"委员会\")>",
                  "sender": "纯路人",
                  "type": "text"
            }
        """
        def internal_callback(raw_msg, chat):
            try:
                LOG.info('--------------Start------------------')
                attr = getattr(raw_msg, 'attr', '')
                # 快速过滤：在消息转换之前过滤，减少不必要的处理
                if attr.lower() in ['weixin', 'system', 'self']:
                    LOG.info(f"ignored system message attr is [{attr}]")
                    return
                LOG.info('------------ Raw message info ------------\n%s', self._dump_obj_attrs(raw_msg))
                LOG.info('------------ Raw chat info ------------\n%s', self._dump_obj_attrs(chat))

                # 使用 chat_info.chat_type 判断群聊（更可靠）
                chat_info = getattr(raw_msg, 'chat_info', {}) or {}
                is_group = chat_info.get('chat_type') == 'group'
                content = getattr(raw_msg, 'content', str(raw_msg))
                is_at_me = is_group and ('@真爱粉' in content or 'zaf' in content.lower())
                if is_group and not is_at_me:
                    LOG.info(
                        f"ignored group message without @ from [{getattr(raw_msg, 'sender', '')}] and chat [{chat_name}]")
                    return

                # 转换消息
                message = convert_message(raw_msg, chat_name)
                LOG.info('Converted message: %r', message.to_dict())
                LOG.info('---------------END-----------------')

                # 调用用户回调
                callback(message, chat_name)
            except Exception as e:
                LOG.error(f"Error in message callback for [{chat_name}]: {e}")
                # 发送错误提示，避免用户感觉假死
                try:
                    self.wx.SendMsg("啊咧？消息好像坏掉了，麻烦再发一次吧~", chat_name)
                except Exception as send_err:
                    LOG.error(f"Failed to send error msg to [{chat_name}]: {send_err}")

        return internal_callback

    def add_message_listener(self, chat_name: str, callback: MessageCallback) -> bool:
        """添加消息监听器"""
        try:
            LOG.info(f"Registering listener for [{chat_name}]")

            internal_callback = self._create_internal_callback(chat_name, callback)
            result = self.wx.AddListenChat(chat_name, internal_callback)
            if self._check_response(result, "AddListenChat", chat_name):
                self._listeners[chat_name] = callback
                return True
            return False
        except Exception as e:
            LOG.error(f"Failed to add listener for [{chat_name}]: {e}")
            return False

    def remove_message_listener(self, chat_name: str, close_window: bool = True) -> bool:
        """
        移除消息监听器
        
        Args:
            chat_name: 要移除的监听聊天对象
            close_window: 是否关闭聊天窗口，默认 True
        """
        try:
            if chat_name not in self._listeners:
                LOG.warning(f"Listener for [{chat_name}] not found in internal dict")
                return True

            result = self.wx.RemoveListenChat(chat_name, close_window=close_window)
            if self._check_response(result, "RemoveListenChat", chat_name):
                del self._listeners[chat_name]
                return True
            return False
        except Exception as e:
            LOG.error(f"Failed to remove listener for [{chat_name}]: {e}")
            return False

    def start_listening(self) -> None:
        """开始消息监听（阻塞）"""
        try:
            LOG.info("Starting message listening...")
            # 检查是否有监听器，如果没有则不调用 KeepRunning
            # wxautox4x 的 KeepRunning 需要先调用 AddListenChat 初始化 _listener_stop_event
            if not self._listeners:
                LOG.warning("No listeners registered, KeepRunning() will not be called")
                LOG.warning("Use API to add listeners first, then restart the service")
                return
            self.wx.KeepRunning()
        except KeyboardInterrupt:
            LOG.info("Listening stopped by user")
        except Exception as e:
            LOG.error(f"Error in message listening: {e}")

    # ==================== 监听恢复 ====================

    def reset_listener(self, chat_name: str) -> dict:
        """
        重置指定聊天的监听
        
        通过关闭子窗口、移除监听、重新添加监听的方式恢复异常的监听。
        
        Args:
            chat_name: 聊天对象名称
            
        Returns:
            重置结果字典，包含:
            - success: 是否成功
            - message: 结果描述
            - steps: 各步骤执行情况
        """
        steps = []
        
        try:
            # 检查是否有该监听
            if chat_name not in self._listeners:
                return {
                    "success": False,
                    "message": f"Listener [{chat_name}] not found",
                    "steps": steps
                }
            
            # 保存原始回调
            original_callback = self._listeners.get(chat_name)
            
            # Step 1: 尝试获取并关闭子窗口
            try:
                sub_window = self.wx.GetSubWindow(chat_name)
                if sub_window:
                    sub_window.Close()
                    steps.append({"step": "close_window", "success": True})
                    LOG.info(f"Closed sub window for [{chat_name}]")
                else:
                    steps.append({"step": "close_window", "success": True, "note": "no window found"})
            except Exception as e:
                steps.append({"step": "close_window", "success": False, "error": str(e)})
                LOG.warning(f"Failed to close sub window for [{chat_name}]: {e}")
            
            # Step 2: 移除监听
            try:
                result = self.wx.RemoveListenChat(chat_name, close_window=True)
                steps.append({"step": "remove_listen", "success": bool(result)})
                LOG.info(f"Removed listener for [{chat_name}]: {result}")
            except Exception as e:
                steps.append({"step": "remove_listen", "success": False, "error": str(e)})
                LOG.warning(f"Failed to remove listener for [{chat_name}]: {e}")
            
            # Step 3: 等待 UI 稳定
            time.sleep(0.5)
            steps.append({"step": "wait", "success": True, "duration": 0.5})
            
            # Step 4: 重新添加监听
            try:
                # 确保 _listeners 中有回调（可能被 RemoveListenChat 清理了）
                if chat_name not in self._listeners and original_callback:
                    self._listeners[chat_name] = original_callback
                
                internal_callback = self._create_internal_callback(chat_name, original_callback)
                result = self.wx.AddListenChat(chat_name, internal_callback)
                if result:
                    steps.append({"step": "add_listen", "success": True})
                    LOG.info(f"Re-added listener for [{chat_name}]")
                    return {
                        "success": True,
                        "message": f"Successfully reset listener for [{chat_name}]",
                        "steps": steps
                    }
                else:
                    steps.append({"step": "add_listen", "success": False})
                    return {
                        "success": False,
                        "message": f"Failed to re-add listener for [{chat_name}]",
                        "steps": steps
                    }
            except Exception as e:
                steps.append({"step": "add_listen", "success": False, "error": str(e)})
                LOG.error(f"Failed to re-add listener for [{chat_name}]: {e}")
                return {
                    "success": False,
                    "message": f"Exception re-adding listener: {e}",
                    "steps": steps
                }
                
        except Exception as e:
            LOG.error(f"Reset listener failed for [{chat_name}]: {e}")
            return {
                "success": False,
                "message": f"Exception: {e}",
                "steps": steps
            }

    def reset_all_listeners(self) -> dict:
        """
        重置所有监听
        
        通过停止所有监听、关闭所有子窗口、切换页面刷新 UI、重新添加所有监听的方式恢复。
        
        Returns:
            重置结果字典，包含:
            - success: 是否成功
            - message: 结果描述
            - total: 总监听数
            - recovered: 成功恢复的列表
            - failed: 恢复失败的列表
            - steps: 各步骤执行情况
        """
        steps = []
        recovered = []
        failed = []
        
        try:
            # 保存当前所有回调
            saved_listeners = dict(self._listeners)
            total = len(saved_listeners)
            
            if total == 0:
                return {
                    "success": True,
                    "message": "No listeners to reset",
                    "total": 0,
                    "recovered": [],
                    "failed": [],
                    "steps": steps
                }
            
            LOG.info(f"Starting reset all listeners, total: {total}")
            
            # Step 1: 停止所有监听
            try:
                self.wx.StopListening(remove=True)
                steps.append({"step": "stop_listening", "success": True})
                LOG.info("Stopped all listening")
            except Exception as e:
                steps.append({"step": "stop_listening", "success": False, "error": str(e)})
                LOG.warning(f"Failed to stop listening: {e}")
            
            # Step 2: 关闭所有子窗口
            closed_count = 0
            try:
                sub_windows = self.wx.GetAllSubWindow()
                for sub_window in sub_windows:
                    try:
                        sub_window.Close()
                        closed_count += 1
                    except Exception as e:
                        LOG.warning(f"Failed to close sub window: {e}")
                steps.append({"step": "close_all_windows", "success": True, "closed": closed_count})
                LOG.info(f"Closed {closed_count} sub windows")
            except Exception as e:
                steps.append({"step": "close_all_windows", "success": False, "error": str(e)})
                LOG.warning(f"Failed to close sub windows: {e}")
            
            # Step 3: 切换页面刷新 UI
            try:
                self.wx.SwitchToContact()
                time.sleep(0.3)
                self.wx.SwitchToChat()
                time.sleep(0.3)
                steps.append({"step": "switch_pages", "success": True})
                LOG.info("Switched pages to refresh UI")
            except Exception as e:
                steps.append({"step": "switch_pages", "success": False, "error": str(e)})
                LOG.warning(f"Failed to switch pages: {e}")
            
            # Step 4: 清空内部监听列表
            self._listeners.clear()
            
            # Step 5: 重新添加所有监听
            for chat_name, callback in saved_listeners.items():
                try:
                    # 重新构建内部回调
                    internal_callback = self._create_internal_callback(chat_name, callback)
                    result = self.wx.AddListenChat(chat_name, internal_callback)
                    if result:
                        # 添加成功，把 callback 加回 _listeners
                        self._listeners[chat_name] = callback
                        recovered.append(chat_name)
                        LOG.info(f"Re-added listener for [{chat_name}]")
                    else:
                        failed.append(chat_name)
                        LOG.error(f"Failed to re-add listener for [{chat_name}]")
                except Exception as e:
                    failed.append(chat_name)
                    LOG.error(f"Exception re-adding listener for [{chat_name}]: {e}")
            
            steps.append({
                "step": "re_add_listeners",
                "success": len(failed) == 0,
                "recovered": len(recovered),
                "failed": len(failed)
            })
            
            success = len(failed) == 0
            return {
                "success": success,
                "message": f"Reset complete: {len(recovered)}/{total} recovered" if success else f"Reset partial: {len(recovered)}/{total} recovered, {len(failed)} failed",
                "total": total,
                "recovered": recovered,
                "failed": failed,
                "steps": steps
            }
            
        except Exception as e:
            LOG.error(f"Reset all listeners failed: {e}")
            return {
                "success": False,
                "message": f"Exception: {e}",
                "total": len(saved_listeners) if 'saved_listeners' in dir() else 0,
                "recovered": recovered,
                "failed": failed,
                "steps": steps
            }

    def health_check(self) -> dict:
        """
        健康检查：检查监听状态是否正常
        
        通过以下方式检测监听健康状态：
        1. 检查窗口是否存在
        2. 对存在的窗口执行主动探测（调用 ChatInfo()），验证窗口是否真正可用
        
        Returns:
            健康检查结果字典，包含:
            - healthy: 是否健康
            - message: 状态描述
            - registered_listeners: 已注册的监听列表
            - active_windows: 活跃的子窗口列表
            - unhealthy_listeners: 异常的监听列表（包含失败原因）
            - orphan_windows: 孤立的窗口列表（有窗口但未注册）
            - probe_results: 主动探测结果详情
        """
        try:
            # 获取已注册的监听
            registered = set(self._listeners.keys())
            
            # 获取所有活跃的子窗口
            active = set()
            window_map = {}  # chat_name -> window object
            try:
                sub_windows = self.wx.GetAllSubWindow()
                for w in sub_windows:
                    try:
                        who = getattr(w, 'who', None)
                        if who:
                            active.add(who)
                            window_map[who] = w
                    except Exception:
                        pass
            except Exception as e:
                LOG.error(f"Failed to get sub windows: {e}")
                return {
                    "healthy": False,
                    "message": f"Failed to get sub windows: {e}",
                    "registered_listeners": list(registered),
                    "active_windows": [],
                    "unhealthy_listeners": [{"chat": c, "reason": "get_windows_failed"} for c in registered],
                    "orphan_windows": [],
                    "probe_results": []
                }
            
            # 主动探测每个已注册的监听
            unhealthy = []
            probe_results = []
            
            for chat_name in registered:
                probe_result = {"chat": chat_name, "window_exists": False, "probe_success": False, "reason": None}
                
                # Step 1: 检查窗口是否存在
                if chat_name not in active:
                    probe_result["reason"] = "window_not_found"
                    unhealthy.append({"chat": chat_name, "reason": "window_not_found"})
                    probe_results.append(probe_result)
                    LOG.warning(f"Health check: [{chat_name}] window not found")
                    continue
                
                probe_result["window_exists"] = True
                
                # Step 2: 主动探测 - 尝试调用 ChatInfo() 验证窗口可用性
                try:
                    window = window_map.get(chat_name)
                    if window:
                        # 尝试获取聊天信息，验证窗口是否真正响应
                        chat_info = window.ChatInfo()
                        if chat_info:
                            probe_result["probe_success"] = True
                            LOG.debug(f"Health check: [{chat_name}] probe success")
                        else:
                            probe_result["reason"] = "chat_info_empty"
                            unhealthy.append({"chat": chat_name, "reason": "chat_info_empty"})
                            LOG.warning(f"Health check: [{chat_name}] ChatInfo returned empty")
                    else:
                        probe_result["reason"] = "window_object_missing"
                        unhealthy.append({"chat": chat_name, "reason": "window_object_missing"})
                        LOG.warning(f"Health check: [{chat_name}] window object missing from map")
                except Exception as e:
                    probe_result["reason"] = f"probe_exception: {str(e)}"
                    unhealthy.append({"chat": chat_name, "reason": f"probe_exception: {str(e)}"})
                    LOG.warning(f"Health check: [{chat_name}] probe exception: {e}")
                
                probe_results.append(probe_result)
            
            # 计算孤立窗口
            orphan = active - registered
            
            # 判断整体健康状态
            healthy = len(unhealthy) == 0
            
            if healthy:
                message = f"All {len(registered)} listeners are healthy"
            else:
                message = f"{len(unhealthy)}/{len(registered)} listeners are unhealthy"
            
            LOG.info(f"Health check: {message}, orphan windows: {len(orphan)}")
            
            return {
                "healthy": healthy,
                "message": message,
                "registered_listeners": list(registered),
                "active_windows": list(active),
                "unhealthy_listeners": unhealthy,
                "orphan_windows": list(orphan),
                "probe_results": probe_results
            }
            
        except Exception as e:
            LOG.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "message": f"Health check exception: {e}",
                "registered_listeners": list(self._listeners.keys()),
                "active_windows": [],
                "unhealthy_listeners": list(self._listeners.keys()),
                "orphan_windows": []
            }

    # ==================== 联系人管理 ====================

    def get_contacts(self) -> dict[str, str]:
        """
        获取联系人列表
        
        Note: wxautox4 基于 UIA，可能无法直接获取完整联系人列表
        """
        try:
            # wxautox4 可能需要通过其他方式获取
            # 这里返回空字典，具体实现需要参考文档
            LOG.warning("get_contacts not fully implemented for wxautox4")
            return {}
        except Exception as e:
            LOG.error(f"Failed to get contacts: {e}")
            return {}

    def get_chat_members(self, chat_name: str) -> dict[str, str]:
        """
        获取群成员列表
        
        Note: wxautox4 基于 UIA，可能无法直接获取群成员
        """
        try:
            # wxautox4 可能需要通过其他方式获取
            LOG.warning("get_chat_members not fully implemented for wxautox4")
            return {}
        except Exception as e:
            LOG.error(f"Failed to get chat members for [{chat_name}]: {e}")
            return {}

    # ==================== 生命周期 ====================

    def is_running(self) -> bool:
        """检查客户端是否运行中"""
        return self._running and self._wx is not None

    def cleanup(self) -> None:
        """清理资源"""
        try:
            self._running = False
            self._listeners.clear()
            LOG.info("WxAutoClient cleaned up")
        except Exception as e:
            LOG.error(f"Error during cleanup: {e}")
