# -*- coding: utf-8 -*-
import json
import logging
from dataclasses import asdict
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models.group_message import GroupMessage

LOG = logging.getLogger("GroupMessageRepository")


class GroupMessageRepository:

    def __init__(self, session: Session):
        self.session = session

    def save(self, msg) -> bool:
        try:
            group_msg = GroupMessage(
                platform=getattr(msg, "platform", "wechat"),
                msg_id=msg.msg_id,
                msg_hash=msg.msg_hash,
                msg_type=msg.msg_type,
                sender_id=msg.sender_id,
                sender_name=msg.sender_name or msg.sender_id,
                chat_id=msg.chat_id,
                chat_name=msg.chat_name or msg.chat_id,
                content=msg.content,
                is_group=msg.is_group,
                is_at_me=msg.is_at_me,
                image_msg=self._serialize(msg.image_msg),
                voice_msg=self._serialize(msg.voice_msg),
                video_msg=self._serialize(msg.video_msg),
                file_msg=self._serialize(msg.file_msg),
                link_msg=self._serialize(msg.link_msg),
                refer_msg=self._serialize(msg.refer_msg),
            )
            self.session.add(group_msg)
            self.session.commit()
            LOG.info("saved msg: platform=%s msg_hash=%s", group_msg.platform, msg.msg_hash)
            return True
        except IntegrityError:
            self.session.rollback()
            LOG.warning("duplicate msg ignored: msg_hash=%s", msg.msg_hash)
            return True
        except Exception as e:
            self.session.rollback()
            LOG.error("save failed: %s", e)
            return False

    @staticmethod
    def _serialize(field) -> Optional[str]:
        if field is None:
            return None
        try:
            return json.dumps(asdict(field), ensure_ascii=False)
        except Exception as e:
            LOG.warning("serialize field failed: %s", e)
            return None

    def get_messages(self, chat_id: str, sender_id: str = None,
                     limit: int = 100, tail_id: int = None,
                     platform: str = None) -> list[dict]:
        try:
            query = self.session.query(GroupMessage).filter(GroupMessage.chat_id == chat_id)
            if platform:
                query = query.filter(GroupMessage.platform == platform)
            if sender_id:
                query = query.filter(GroupMessage.sender_id == sender_id)
            if tail_id is not None:
                query = query.filter(GroupMessage.id < tail_id)
            messages = query.order_by(GroupMessage.created_at.desc()).limit(limit).all()
            messages.reverse()
            return [
                {
                    "id": msg.id,
                    "platform": msg.platform,
                    "msg_id": msg.msg_id,
                    "msg_type": msg.msg_type,
                    "chat_id": msg.chat_id,
                    "chat_name": msg.chat_name,
                    "sender_id": msg.sender_id,
                    "sender_name": msg.sender_name,
                    "content": msg.content,
                    "created_at": msg.created_at.strftime('%Y-%m-%d %H:%M:%S') if msg.created_at else None,
                }
                for msg in messages
            ]
        except Exception as e:
            LOG.error("get_messages failed: chat_id=%s err=%s", chat_id, e)

            return []
