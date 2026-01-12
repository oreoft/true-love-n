# -*- coding: utf-8 -*-
"""
群消息记录仓储层

负责群消息的持久化操作。
"""

import json
import logging
import time
from dataclasses import asdict
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError

from ..models.group_message import GroupMessage

LOG = logging.getLogger("GroupMessageRepository")

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 0.5  # 秒


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
        保存群消息记录（带重试机制）
        
        Args:
            chat_message: ChatMessage 对象
            
        Returns:
            是否保存成功
        """
        last_error = None

        for attempt in range(MAX_RETRIES):
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

                LOG.debug(f"Successfully saved group message: msg_hash={chat_message.msg_hash}")
                return True

            except IntegrityError:
                # 唯一索引冲突（重复消息），回滚并忽略
                self.session.rollback()
                LOG.debug(f"Duplicate message ignored: msg_hash={chat_message.msg_hash}")
                return True  # 重复消息也算成功

            except OperationalError as e:
                # 数据库锁定错误，重试
                self.session.rollback()
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    LOG.warning(f"Database locked, retrying ({attempt + 1}/{MAX_RETRIES}): {e}")
                    time.sleep(RETRY_DELAY * (attempt + 1))  # 递增延迟
                continue

            except Exception as e:
                # 其他异常，回滚并记录错误
                self.session.rollback()
                LOG.error(f"Failed to save group message: {e}")
                return False

        # 所有重试都失败
        LOG.error(f"Failed to save group message after {MAX_RETRIES} retries: {last_error}")
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
