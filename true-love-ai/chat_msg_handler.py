import logging

import chatgpt
from configuration import Config


# 封装抽象层调用
class ChatMsgHandler:
    def __init__(self):
        self.LOG = logging.getLogger("ChatMsgHandler")
        config = Config()
        # 默认是none
        self.chatbot = None
        # 如果是chatgpt
        if config.ENABLE_BOT == chatgpt.name:
            self.chatbot = chatgpt.ChatGPT()

    def get_answer(self, question: str, wxid: str, sender: str) -> str:
        if '询问-' in question:
            return self.chatbot.get_xun_wen(question)
        if self.chatbot:
            return self.chatbot.get_answer(question, wxid, sender)
        self.LOG.info("self.chatbot配置为空, 但是调用了get_answer方法")
        return ""

    def get_img(self, question: str, wxid: str, sender: str) -> str:
        self.chatbot.get_img(question)
        self.LOG.info("self.chatbot配置为空, 但是调用了get_img方法")
        return ""

if __name__ == "__main__":
    print(ChatMsgHandler().get_answer("你好", "13", "3"))
