import logging
import re

from models.wx_msg import WxMsgServer
from trig_msg_handler import *


class MsgHandler:

    def __int__(self):
        self.LOG = logging.getLogger("MsgHandler")

    def handler_msg(self, msg: WxMsgServer) -> str:
        q: str = re.sub(r"@.*?[\u2005|\s]", "", msg.content).strip()

        # 如果是查询任务
        if q.startswith('查询'):
            self.LOG.info(f"收到:{msg.sender}, 查询任务:{q}")
            res = TrigSearchHandler.run(q)

        # 如果是执行任务
        elif q.startswith('执行'):
            self.LOG.info(f"收到:{msg.sender}, 执行任务:{q}")
            res = TrigTaskHandler.run(q)

        # 如果聊天没开
        elif not self.chat:  # 没接 ChatGPT，固定回复
            res = "你@我干嘛？"

        # 其他默认是联调消息
        else:
            res = self.chat.get_answer(q, (msg.roomid if msg.from_group() else msg.sender), msg.sender)

        return res
