import logging
import re

from models.wx_msg import WxMsgServer
from trig_msg_handler import *


# 抽象接口
class ChatBot:
    def get_answer(self, question: str, wxid: str, sender: str) -> str:
        pass


class MsgHandler:

    def __int__(self):
        self.LOG = logging.getLogger("MsgHandler")

    def handler_msg(self, msg: WxMsgServer) -> str:
        q: str = re.sub(r"@.*?[\u2005|\s]", "", msg.content).strip()

        # 如果是查询任务
        if q.startswith('查询'):
            self.LOG.info(f"收到:{msg.sender}, 查询任务:{q}")
            return TrigSearchHandler().run(q)

        # 如果是执行任务
        if q.startswith('执行'):
            self.LOG.info(f"收到:{msg.sender}, 执行任务:{q}")
            return TrigTaskHandler().run(q)

        # 如果聊天没开
        from chat_msg_handler import ChatMsgHandler
        handler = ChatMsgHandler()
        # 没接 大模型，固定回复
        if not handler.chatbot:
            return "你@我干嘛？"

        # 其他默认是联调消息
        else:
            return handler.get_answer(q, (msg.roomid if msg.from_group() else msg.sender), msg.sender)
