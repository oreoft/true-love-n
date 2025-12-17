# -*- coding: utf-8 -*-
"""
消息转换器 - 简化版

将 wxautox4 的消息对象转换为统一的 ChatMessage 模型。

文件路径处理说明：
- 媒体文件下载到 Server 的 wx_imgs 目录（通过 WxParam.DEFAULT_SAVE_PATH 设置）
- 下载后转换为相对路径（如 wx_imgs/filename.jpg）传输给 Server
- Server 可以直接使用相对路径访问文件
"""

import logging
from typing import Any, Optional

from true_love_base.models.message import (
    ChatMessage,
    ImageMsg,
    VoiceMsg,
    VideoMsg,
    FileMsg,
    LinkMsg,
)
from true_love_base.utils.path_resolver import to_server_path

LOG = logging.getLogger("MessageConverter")

# 引用内容 → 消息类型映射
QUOTE_TYPE_MAP = {
    '图片': 'image',
    '[图片]': 'image',
    '视频': 'video',
    '[视频]': 'video',
    '语音': 'voice',
    '[语音]': 'voice',
    '文件': 'file',
    '[文件]': 'file',
}


def convert_message(
    raw_msg: Any,
    chat_name: str,
    is_group: bool = False,
    is_at_me: bool = False
) -> ChatMessage:
    """
    将 wxautox4 消息转换为 ChatMessage
    
    Args:
        raw_msg: wxautox4 的原始消息对象
        chat_name: 聊天对象名称
        is_group: 是否群聊
        is_at_me: 是否@了机器人
        
    Returns:
        ChatMessage 实例
    """
    try:
        msg_type = getattr(raw_msg, 'type', 'text')
        sender = getattr(raw_msg, 'sender', chat_name)
        content = getattr(raw_msg, 'content', str(raw_msg))
        
        # 判断是否自己发送的消息（wxautox4 的 attr 属性）
        attr = getattr(raw_msg, 'attr', '')
        is_self = attr == 'self'
        
        # 如果 sender 是 wxauto 的消息属性标识，用 chat_name 替代
        if sender in ('friend', 'self', ''):
            sender = chat_name
        
        # 构建基础消息
        msg = ChatMessage(
            msg_type=msg_type if msg_type != 'quote' else 'refer',
            sender=sender,
            chat_id=chat_name,
            content=content,
            is_group=is_group,
            is_self=is_self,
            is_at_me=is_at_me,
            raw_msg=raw_msg,
        )
        
        # 按类型填充特有字段
        if msg_type == 'image':
            file_path = _download(raw_msg, "image")
            msg.image_msg = ImageMsg(file_path=file_path)
            
        elif msg_type == 'voice':
            text_content = _to_text(raw_msg)
            msg.voice_msg = VoiceMsg(text_content=text_content)
            # 如果有转文字结果，用它作为 content
            if text_content:
                msg.content = text_content
                
        elif msg_type == 'video':
            file_path = _download(raw_msg, "video")
            msg.video_msg = VideoMsg(file_path=file_path)
            
        elif msg_type == 'file':
            file_path = _download(raw_msg, "file")
            file_name = getattr(raw_msg, 'file_name', None) or getattr(raw_msg, 'filename', None)
            msg.file_msg = FileMsg(file_path=file_path, file_name=file_name)
            
        elif msg_type == 'link':
            url = raw_msg.get_url() if hasattr(raw_msg, 'get_url') else None
            msg.link_msg = LinkMsg(url=url)
            
        elif msg_type == 'quote':
            msg.refer_msg = _build_refer_msg(raw_msg, chat_name, is_group)
        
        return msg
        
    except Exception as e:
        LOG.error(f"Failed to convert message: {e}")
        return ChatMessage(
            msg_type='text',
            sender=chat_name,
            chat_id=chat_name,
            content=str(raw_msg),
            is_group=is_group,
            raw_msg=raw_msg,
        )


def _download(raw_msg: Any, media_type: str) -> Optional[str]:
    """
    下载媒体文件，返回 Server 可用的相对路径
    
    wxautox4 会将文件下载到 WxParam.DEFAULT_SAVE_PATH（已设置为 server/wx_imgs）
    下载后将完整路径转换为相对路径（如 wx_imgs/filename.jpg）供 Server 直接使用
    
    Args:
        raw_msg: wxautox4 消息对象
        media_type: 媒体类型（用于日志）
        
    Returns:
        Server 可用的相对路径，如 "wx_imgs/filename.jpg"
    """
    if not hasattr(raw_msg, 'download'):
        return None
    try:
        # wxautox4 下载文件，返回完整路径
        full_path = raw_msg.download()
        if not full_path:
            return None
        
        # 转换为 Server 可用的相对路径
        relative_path = to_server_path(str(full_path))
        LOG.debug(f"Downloaded {media_type}: {full_path} -> {relative_path}")
        return relative_path
    except Exception as e:
        LOG.warning(f"Failed to download {media_type}: {e}")
        return None


def _to_text(raw_msg: Any) -> Optional[str]:
    """语音转文字"""
    if not hasattr(raw_msg, 'to_text'):
        return None
    try:
        text = raw_msg.to_text()
        LOG.debug(f"Voice to_text: {text}")
        return text
    except Exception as e:
        LOG.warning(f"Voice to_text failed: {e}")
        return None


def _build_refer_msg(raw_msg: Any, chat_name: str, is_group: bool) -> ChatMessage:
    """
    构建引用消息
    
    wxauto 的 QuoteMessage 结构：
    - content: 用户输入的回复文字
    - quote_content: 被引用的内容（字符串，如 "图片"、"视频" 或实际文字）
    - quote_nickname: 被引用消息的发送者
    """
    quote_content = getattr(raw_msg, 'quote_content', '')
    quote_sender = getattr(raw_msg, 'quote_nickname', '') or 'unknown'
    
    # 判断被引用的内容类型
    refer_type = QUOTE_TYPE_MAP.get(quote_content, 'text')
    
    LOG.info(f"Building refer_msg: type={refer_type}, content={quote_content}, sender={quote_sender}")
    
    return ChatMessage(
        msg_type=refer_type,
        sender=quote_sender,
        chat_id=chat_name,
        content=quote_content if refer_type == 'text' else '',
        is_group=is_group,
    )
