import json
import logging
import re

import context_vars
from asr_utils import do_asr
from chat_msg_handler import ChatMsgHandler
from models.wx_msg import WxMsgServer
from trig_remainder_handler import TrigRemainderHandler
from trig_search_handler import TrigSearchHandler
from trig_task_handler import TrigTaskHandler

handler = ChatMsgHandler()
LOG = logging.getLogger("MsgHandler")

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
            return TrigTaskHandler().run(q, msg.sender, msg.roomid)

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
            return handler.gen_img_by_img(q, msg.refer_chat['content'],
                                          (msg.roomid if msg.from_group() else msg.sender),
                                          msg.sender)

        # 如果提示词生图, 直接去生图
        if q.startswith('生成') and ('片' in q or '图' in q):
            self.LOG.info(f"收到:{msg.sender}, 生成图片:{q}")
            return handler.gen_img(q, (msg.roomid if msg.from_group() else msg.sender), msg.sender)

        # 如果是引用文本或者链接消息, 那么拼接一下引用的内容
        if msg.refer_chat and msg.refer_chat['type'] in [1, 4, 5]:
            #  默认文本消息
            refer_text = msg.refer_chat['content']
            url = self.extract_first_link(msg.refer_chat['content'])
            # 如果是文本但是含链接
            if msg.refer_chat['type'] in [1] and url is not None:
                refer_text = self.crawl_content(url)
            # 如果是链接, 去爬虫
            if msg.refer_chat['type'] in [4, 5]:
                refer_text = self.crawl_content(json.loads(msg.refer_chat['content']['url']))
            q = f"{q}, quoted content:{refer_text}"
            LOG.info(f"收到引用文本, 现在get_answer:{q}")
            return handler.get_answer(q, (msg.roomid if msg.from_group() else msg.sender), msg.sender)
        # 如果引用语音消息或者附件为语音, 那么去asr一下
        if msg.refer_chat and (msg.refer_chat['type'] in [34]
                               or (msg.refer_chat['type'] == 6
                                   and ('m4a' in msg.refer_chat['content'] or 'mp3' in msg.refer_chat['content']))):
            q = f"{q}, quoted asr recognition content content:{do_asr(msg.refer_chat['content'])}"
            return handler.get_answer(q, (msg.roomid if msg.from_group() else msg.sender),
                                      msg.sender)
        # 其他引用类型说不支持
        if msg.refer_chat:
            return "啊哦~ 现在这个类型引用我还看不懂, 不如你把内容复制出来给我看看呢"

        # 如果是文本消息, 并且包含链接
        url = self.extract_first_link(q)
        if msg.type == 1 and url is not None:
            q = f"{q}, quoted content:{self.crawl_content(url)}"
            return handler.get_answer(q, (msg.roomid if msg.from_group() else msg.sender), msg.sender)

        # 如果是文本消息
        if msg.type == 1:
            return handler.get_answer(q, (msg.roomid if msg.from_group() else msg.sender), msg.sender)

        # 如果是私聊,并且是图片, 直接进行分析
        if msg.type == 3 and not msg.from_group():
            return handler.gen_img_by_img('请分析图片或者回答图片内容', msg.content,
                                          (msg.roomid if msg.from_group() else msg.sender),
                                          msg.sender)

        # 如果是语音消息, 那么去asr一下
        if msg.type == 34:
            return handler.get_answer(do_asr(msg.content), (msg.roomid if msg.from_group() else msg.sender),
                                      msg.sender)
        # 其他类型
        return "啊哦~ 现在这个消息暂时我还看不懂, 但我会持续学习的~"

    @staticmethod
    def extract_first_link(text):
        # 正则表达式用于检测文本中的所有URL
        url_pattern = re.compile(r'https?://[^\s]+')
        match = url_pattern.search(text)
        if match:
            return match.group()  # 返回第一个匹配的链接
        return None  # 如果没有匹配，返回 None

    @staticmethod
    def crawl_content(url):
        if url == "" or url is None:
            return ""
        try:
            import requests
            request_url = "https://r.jina.ai/" + url
            headers = {'Accept': 'application/json', 'User-Agent': 'PostmanRuntime/7.40.0'}
            response = requests.get(url=request_url, headers=headers)
            response_data = response.json()
            return re.sub(r'\(http.*?\)', '', response_data['data']['content']).replace('[]', '').replace('\n\n',
                                                                                                          '\n').strip()
        except Exception:
            logging.exception(f"crawl_content error, url:{url}")
            return '内容解析失败'


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
