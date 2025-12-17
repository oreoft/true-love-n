# -*- coding: utf-8 -*-
"""
WxAuto Adapter - wxautox4 SDK 适配器

实现 WeChatClientProtocol 接口，封装 wxautox4 的具体调用。
"""

import logging
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

    def add_message_listener(self, chat_name: str, callback: MessageCallback) -> bool:
        """添加消息监听器"""
        try:
            LOG.info(f"Registering listener for [{chat_name}]")

            # 创建内部回调，转换消息格式
            # 注意：wxauto 回调签名是 (msg, chat)，必须接收两个参数
            def internal_callback(raw_msg, chat):
                try:

                    # if exists, log raw_msg.type and raw_msg.attr
                    LOG.info('--------------------------------')
                    LOG.info('Raw message: %r', raw_msg)
                    if hasattr(raw_msg, 'type'):
                        LOG.info('Raw message type: %s', raw_msg.type)
                    if hasattr(raw_msg, 'attr'):
                        LOG.info('Raw message attr: %r', raw_msg.attr)

                    # 获取 sender 属性
                    sender = getattr(raw_msg, 'sender', '')

                    # 判断是否群聊：
                    # 1. sender 为空或等于 chat_name -> 私聊
                    # 2. sender 为 'friend' 或 'self' -> 私聊（这是 wxauto 的消息属性标识，不是真正的发送者）
                    # 3. 其他情况（sender 是群成员昵称）-> 群聊
                    is_group = bool(
                        sender
                        and sender != chat_name
                        and sender not in ('friend', 'self')
                    )

                    # 如果 sender 是属性标识，用 chat_name 作为实际发送者
                    if sender in ('friend', 'self', ''):
                        sender = chat_name

                    LOG.debug(f"Message callback: chat_name={chat_name}, sender={sender}, is_group={is_group}")

                    # 转换消息
                    message = convert_message(raw_msg, chat_name, is_group)
                    LOG.info('Converted message: %r', message.to_dict())
                    LOG.info('--------------------------------')

                    # 检测是否@了自己
                    if hasattr(raw_msg, 'content'):
                        content = str(getattr(raw_msg, 'content', ''))
                        self_name = self.get_self_name()
                        is_at = f"@{self_name}" in content or '@真爱粉' in content or 'zaf' in content.lower()
                        if is_group:
                            message.is_at_me = is_at
                        LOG.debug(f"@ detection: content={content[:50]}, self_name={self_name}, is_at={is_at}")

                    # 调用用户回调
                    callback(message, chat_name)
                except Exception as e:
                    LOG.error(f"Error in message callback for [{chat_name}]: {e}")
                    # 发送错误提示，避免用户感觉假死
                    try:
                        raw_msg.quote("啊咧？消息好像坏掉了，麻烦再发一次吧~")
                    except Exception as send_err:
                        LOG.error(f"Failed to send error msg to [{chat_name}]: {send_err}")

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
