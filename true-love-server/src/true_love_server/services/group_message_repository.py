# -*- coding: utf-8 -*-
"""
群消息记录仓储层

负责群消息的持久化操作。
"""

import json
import logging
from dataclasses import asdict
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..models.group_message import GroupMessage

LOG = logging.getLogger("GroupMessageRepository")


class GroupMessageRepository:
    """群消息仓储类"""

    def __init__(self, session: Session):
        """
        初始化仓储
        
        Args:
            session: SQLAlchemy Session
        """
        self.session = session

    def save(self, chat_message) -> bool:
        """
        保存群消息记录
        
        Args:
            chat_message: ChatMessage 对象
            
        Returns:
            是否保存成功
        """
        try:
            # 将 ChatMessage 转换为 GroupMessage ORM 对象
            group_msg = GroupMessage(
                msg_id=chat_message.msg_id,
                msg_hash=chat_message.msg_hash,
                msg_type=chat_message.msg_type,
                sender=chat_message.sender,
                chat_id=chat_message.chat_id,
                content=chat_message.content,
                is_group=chat_message.is_group,
                is_at_me=chat_message.is_at_me,
                image_msg=self._serialize_field(chat_message.image_msg),
                voice_msg=self._serialize_field(chat_message.voice_msg),
                video_msg=self._serialize_field(chat_message.video_msg),
                file_msg=self._serialize_field(chat_message.file_msg),
                link_msg=self._serialize_field(chat_message.link_msg),
                refer_msg=self._serialize_field(chat_message.refer_msg),
            )
            
            # 添加到 session 并提交
            self.session.add(group_msg)
            self.session.commit()
            
            LOG.info(f"Successfully saved group message: msg_hash={chat_message.msg_hash}")
            return True
            
        except IntegrityError:
            self.session.rollback()
            LOG.warning(f"Duplicate message ignored: msg_hash={chat_message.msg_hash}")
            return True  # 重复消息也算成功
            
        except Exception as e:
            # 其他异常，回滚并记录错误
            self.session.rollback()
            LOG.error(f"Failed to save group message: {e}")
            return False

    @staticmethod
    def _serialize_field(field) -> Optional[str]:
        """
        将嵌套对象序列化为 JSON 字符串
        
        Args:
            field: 字段对象（如 ImageMsg, VoiceMsg 等）
            
        Returns:
            JSON 字符串或 None
        """
        if field is None:
            return None

        try:
            # 如果是 dataclass，使用 asdict 转换
            field_dict = asdict(field)
            return json.dumps(field_dict, ensure_ascii=False)
        except Exception as e:
            LOG.warning(f"Failed to serialize field: {e}")
            return None

    def get_messages(self, chat_id: str, sender: str = None,
                     limit: int = 100, tail_id: int = None) -> list[dict]:
        """
        查询群消息，支持按发送者过滤和游标分页。

        Args:
            chat_id: 群聊ID
            sender: 发送者昵称，None 则查全群
            limit: 返回最大条数
            tail_id: 游标，仅返回 id < tail_id 的消息（用于向前翻页，预留）
        """
        try:
            query = self.session.query(GroupMessage).filter(GroupMessage.chat_id == chat_id)
            if sender:
                query = query.filter(GroupMessage.sender == sender)
            if tail_id is not None:
                query = query.filter(GroupMessage.id < tail_id)
            messages = query.order_by(GroupMessage.created_at.desc()).limit(limit).all()
            messages.reverse()
            return [
                {
                    "id": msg.id,
                    "msg_id": msg.msg_id,
                    "chat_id": msg.chat_id,
                    "sender": msg.sender,
                    "content": msg.content,
                    "created_at": msg.created_at.strftime('%Y-%m-%d %H:%M:%S') if msg.created_at else None,
                }
                for msg in messages
            ]
        except Exception as e:
            LOG.error(f"Failed to fetch messages for chat_id={chat_id}, sender={sender}: {e}")
            return []
