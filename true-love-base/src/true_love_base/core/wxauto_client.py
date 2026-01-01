# -*- coding: utf-8 -*-
"""
WxAuto WxAutoClient - wxautox4 SDK 封装客户端

实现 WeChatClientProtocol 接口，封装 wxautox4 的具体调用。
"""

import json
import logging
from typing import Callable, Optional

# This is a special import, please do not modify
from true_love_base.wxautox4x.wxautox4x import WeChat
from wxautox4.param import WxParam

from true_love_base.models.message_converter import convert_message
from true_love_base.models import ChatMessage
from true_love_base.utils.path_resolver import get_wx_imgs_dir
from true_love_base.services import server_client

LOG = logging.getLogger("WxAutoClient")

# 设置 wxauto 默认文件保存路径到 server 的 wx_imgs 目录
WxParam.CHAT_WINDOW_SIZE = (8000, 6000)
_wx_imgs_dir = get_wx_imgs_dir()
if _wx_imgs_dir:
    WxParam.DEFAULT_SAVE_PATH = _wx_imgs_dir
    LOG.info(f"Set WxParam.DEFAULT_SAVE_PATH to: {_wx_imgs_dir}")

MessageCallback = Callable[[ChatMessage, str], None]


class WxAutoClient():
    """
    wxautox4 客户端适配器 封装 wxautox4 的所有操作。
    """

    def __init__(self):
        """初始化 wxautox4 客户端"""
        self._wx = None
        self._running = False
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
            LOG.debug(f"SendMsg content: {content[:50]}...")
            sub_window = self.wx.GetSubWindow(receiver)
            result = sub_window.SendMsg(content) if sub_window else self.wx.SendMsg(content, receiver)
            return self._check_response(result, "SendMsg", receiver)
        except Exception as e:
            LOG.error(f"Failed to send text to [{receiver}]: {e}")
            return False

    def send_file(self, receiver: str, file_path: str) -> bool:
        """发送文件"""
        try:
            LOG.debug(f"SendFiles path: {file_path}")
            sub_window = self.wx.GetSubWindow(receiver)
            result = sub_window.SendFiles(file_path) if sub_window else self.wx.SendFiles(file_path, receiver)
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
                trigger_word = "真爱粉" if raw_msg.type == 'voice' else "@真爱粉"
                is_at_me = is_group and (trigger_word in content or 'zaf' in content.lower())
                # 判断content是否超过 15行
                if is_group and content.count('\n') > 15:
                    # 随便回复点二次元内容，把消息顶上去
                    res = self.wx.SendMsg("(｡･ω･｡)ﾉ♡", chat_name)
                    LOG.info("Replied to long message in group to push it up: %r", res)

                # 转换消息
                message = convert_message(raw_msg, chat_name, is_at_me)
                LOG.info('Converted message: %r', message.to_dict())
                LOG.info('---------------END-----------------')

                # 异步记录群消息（不阻塞主流程）
                server_client.record_group_message_async(message)

                if is_group and not is_at_me:
                    LOG.info(
                        f"ignored group message without @ from [{getattr(raw_msg, 'sender', '')}] and chat [{chat_name}]")
                    return

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
            return self._check_response(result, "AddListenChat", chat_name)
        except Exception as e:
            LOG.error(f"Failed to add listener for [{chat_name}]: {e}")
            return False

    def start_listening(self) -> None:
        """开始消息监听（阻塞）"""
        try:
            LOG.info("Starting message listening...")
            self.wx.KeepRunning()
        except KeyboardInterrupt:
            LOG.info("Listening stopped by user")
        except Exception as e:
            LOG.error(f"Error in message listening: {e}")

    # ==================== 生命周期 ====================

    def is_running(self) -> bool:
        """检查客户端是否运行中"""
        return self._running and self._wx is not None

    def cleanup(self) -> None:
        """清理资源"""
        try:
            self._running = False
            LOG.info("WxAutoClient cleaned up")
        except Exception as e:
            LOG.error(f"Error during cleanup: {e}")
