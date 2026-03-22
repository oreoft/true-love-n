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
            # 唯一索引冲突（重复消息），回滚并忽略
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

    def get_recent_messages(self, chat_id: str, sender: str, limit: int = 100) -> list[dict]:
        """
        获取指定群聊中某个特定用户的最近N条发言
        
        Args:
            chat_id: 群聊ID
            sender: 发送者
            limit: 返回的最大消息数量
            
        Returns:
            以字典形式返回最近发言的列表
        """
        try:
            query = self.session.query(GroupMessage).filter(
                GroupMessage.chat_id == chat_id,
                GroupMessage.sender == sender
            ).order_by(GroupMessage.created_at.desc()).limit(limit)
            
            # 由于查出来是倒序的（最新的在前面），我们在返回时翻转使其按照时间正序排列
            messages = query.all()
            messages.reverse()
            
            result = []
            for msg in messages:
                result.append({
                    "msg_id": msg.msg_id,
                    "chat_id": msg.chat_id,
                    "sender": msg.sender,
                    "content": msg.content,
                    "created_at": msg.created_at.strftime('%Y-%m-%d %H:%M:%S') if msg.created_at else None
                })
            return result
        except Exception as e:
            LOG.error(f"Failed to fetch recent messages for chat_id={chat_id}, sender={sender}: {e}")
            return []
