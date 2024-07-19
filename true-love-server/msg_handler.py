import logging

import context_vars
from chat_msg_handler import ChatMsgHandler
from models.wx_msg import WxMsgServer
from trig_remainder_handler import TrigRemainderHandler
from trig_search_handler import TrigSearchHandler
from trig_task_handler import TrigTaskHandler

handler = ChatMsgHandler()


class MsgHandler:

    def __init__(self):
        self.LOG = logging.getLogger("MsgHandler")

    def handler_msg(self, msg: WxMsgServer) -> str:
        q: str = msg.content.replace("@真爱粉", "").replace("zaf", "").strip()
        context_vars.local_msg_id.set(msg.id)
        # 如果是查询任务
        if q.startswith('$查询'):
            self.LOG.info(f"收到:{msg.sender}, 查询任务:{q}")
            return TrigSearchHandler().run(q)

        # 如果是执行任务
        if q.startswith('$执行'):
            self.LOG.info(f"收到:{msg.sender}, 执行任务:{q}")
            return TrigTaskHandler().run(q, msg.sender)

        # 如果是提醒任务
        if q.startswith('$提醒'):
            self.LOG.info(f"收到:{msg.sender}, 提醒任务:{q}")
            return TrigRemainderHandler().router(q, (msg.roomid if msg.from_group() else msg.sender), msg.sender)

        # 如果聊天没开 没接 大模型，固定回复
        if not handler.chatbot:
            return "你@我干嘛？"

        # 如果图片引用类型, 把图片和内容送去大模型, 看是分析还是图生图
        if msg.refer_chat and msg.refer_chat['type'] == 3:
            self.LOG.info(f"收到引用图片, 现在需要去大模型判断分析还是生图:{q}")
            return handler.gen_img_by_img(q, msg.refer_chat['content'], (msg.roomid if msg.from_group() else msg.sender),
                                          msg.sender)

        # 如果提示词生图, 直接去生图
        if q.startswith('生成') and ('片' in q or '图' in q):
            self.LOG.info(f"收到:{msg.sender}, 生成图片:{q}")
            return handler.gen_img(q, (msg.roomid if msg.from_group() else msg.sender), msg.sender)

        # 如果是引用文本消息, 那么拼接一下引用的内容
        if msg.refer_chat and msg.refer_chat['type'] == 1:
            q = f"{q}, quoted content:{msg.refer_chat['content']}"

        # 如果是文本消息
        if msg.type == 1:
            return handler.get_answer(q, (msg.roomid if msg.from_group() else msg.sender), msg.sender)
        # 其他引用类型 都说不支持
        return "啊哦~ 现在这个类型引用我还看不懂, 不如你把内容复制出来给我看看呢"


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
