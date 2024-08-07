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
        if self.chatbot:
            return self.chatbot.async_get_answer(question, wxid, sender)
        self.LOG.info("self.chatbot配置为空, 但是调用了get_answer方法")
        return ""

    def gen_img(self, question: str, wxid: str, sender: str) -> str:
        if self.chatbot:
            return self.chatbot.async_gen_img(question, wxid, sender)
        self.LOG.info("self.chatbot配置为空, 但是调用了gen_img方法")
        return ""

    def gen_img_by_img(self, question: str, img_path: str, wxid: str, sender: str) -> str:
        if self.chatbot:
            return self.chatbot.async_gen_img_by_img(question, img_path, wxid, sender)

        self.LOG.info("self.chatbot配置为空, 但是调用了gen_img_by_img方法")
        return ""


if __name__ == "__main__":
    print(ChatMsgHandler().get_answer("你好", "13", "3"))
