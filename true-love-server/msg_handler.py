import logging
import re

from models.wx_msg import WxMsgServer
from trig_remainder_handler import TrigRemainderHandler
from trig_search_handler import TrigSearchHandler
from trig_task_handler import TrigTaskHandler


# 抽象接口
class ChatBot:
    def get_answer(self, question: str, wxid: str, sender: str) -> str:
        pass


class MsgHandler:

    def __init__(self):
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
            return TrigTaskHandler().run(q, msg.sender)

        # 如果是提醒任务
        if q.startswith('提醒'):
            self.LOG.info(f"收到:{msg.sender}, 提醒任务:{q}")
            return TrigRemainderHandler().router(q, (msg.roomid if msg.from_group() else msg.sender), msg.sender)

        # 如果聊天没开
        from chat_msg_handler import ChatMsgHandler
        handler = ChatMsgHandler()
        # 没接 大模型，固定回复
        if not handler.chatbot:
            return "你@我干嘛？"

        # 如果是生图
        if q.startswith('生成') and '片' in q:
            self.LOG.info(f"收到:{msg.sender}, 生成图片:{q}")
            return handler.gen_img(q, (msg.roomid if msg.from_group() else msg.sender), msg.sender)

        # 其他默认是聊天消息
        else:
            return handler.get_answer(q, (msg.roomid if msg.from_group() else msg.sender), msg.sender)


if __name__ == "__main__":
    handler = MsgHandler()
    while True:
        q = input(">>> ")
        msg = {
            "sender": "123",
            "roomid": "123",
            "content": q,
            "_is_group": False
        }
        print(handler.handler_msg(WxMsgServer(msg)))
