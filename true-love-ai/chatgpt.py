#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import time
from datetime import datetime

import httpx
from openai import OpenAI

from configuration import Config

name = "chatgpt"


class ChatGPT:

    def __init__(self) -> None:
        self.LOG = logging.getLogger("MsgHandler")

        self.config = Config().LLM_BOT
        # 自己搭建或第三方代理的接口
        self.openai = OpenAI(timeout=30, api_key=self.config.get("key3"))
        self.openai.base_url = self.config.get("api")
        # 代理
        proxy = self.config.get("proxy")
        if proxy:
            self.openai.http_client = httpx.Client(proxies=proxy)
        self.conversation_list = {}
        self.system_content_msg = {"role": "system", "content": self.config.get("prompt")}
        self.system_content_msg2 = {"role": "system", "content": self.config.get("prompt2")}
        self.system_content_msg3 = {"role": "system", "content": self.config.get("prompt3")}
        # 轮训负载key的计数器
        self.count = 0

    def get_xun_wen(self, question):
        method_name = question.split("-")[1]
        return self.send_xun_wen(method_name)

    def send_xun_wen(self, content):
        rsp = ''
        try:
            self.openai.api_key = self.config.get("key3")
            # 发送请求
            ret = self.openai.chat.completions.create(
                model="gpt-4-turbo",
                messages=[self.system_content_msg3, {"role": "user", "content": content}],
                temperature=0.2,
                stream=True
            )
            # 获取stream查询
            for stream_res in ret:
                if stream_res.choices[0].delta.content:
                    rsp += stream_res.choices[0].delta.content.replace('\n\n', '\n')
        except Exception as e0:
            rsp = "An unknown error has occurred. Try again later."
            self.LOG.error(str(e0))
        return rsp

    def send_chatgpt(self, real_model, wxid):
        rsp = ''
        try:
            # 发送请求
            ret = self.openai.chat.completions.create(
                model=real_model,
                messages=self.conversation_list[wxid],
                temperature=0.2,
                stream=True
            )
            # 获取stream查询
            for stream_res in ret:
                if stream_res.choices[0].delta.content:
                    rsp += stream_res.choices[0].delta.content.replace('\n\n', '\n')
            self._update_message(wxid, rsp, "assistant")
        except Exception as e0:
            rsp = "发生未知错误, 稍后再试试捏"
            self.LOG.error(str(e0))
        return rsp

    def get_answer(self, question: str, wxid: str, sender: str) -> str:
        # 走chatgpt wxid或者roomid,个人时为微信id，群消息时为群id
        self._update_message(wxid, question.replace("debug", "", 1), "user")
        self.count += 1
        cases = {
            0: self.config.get("key1"),
            1: self.config.get("key2"),
            2: self.config.get("key3"),
        }
        real_key = cases.get(self.count % 3, self.config.get("key1"))
        real_model = "gpt-3.5-turbo"
        # 如果是有权限访问gpt4的，直接走gpt4
        # if sender in self.config.get("gpt4") and ('gpt4' in question or 'GPT4' in question):
        if sender in self.config.get("gpt4"):
            real_key = self.config.get("key2")
            real_model = "gpt-4-0125-preview"
        real_model = "gpt-4-turbo"
        self.openai.api_key = real_key
        start_time = time.time()
        self.LOG.info("开始发送给chatgpt， 其中real_key: %s, real_model: %s", real_key[-4:], real_model)
        rsp = self.send_chatgpt(real_model, wxid)
        end_time = time.time()
        cost = round(end_time - start_time, 2)
        self.LOG.info("chat回答时间为：%s 秒", cost)
        if question.startswith('debug'):
            return rsp + '\n\n' + '(cost: ' + str(cost) + 's, use: ' + real_key[-4:] + ', model: ' + real_model + ')'
        else:
            return rsp

    def _update_message(self, wxid: str, question: str, role: str) -> None:
        now_time = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        time_mk = "当需要回答时间时请直接参考回复:"
        # 初始化聊天记录,组装系统信息
        if wxid not in self.conversation_list.keys():
            question_ = [
                self.system_content_msg if wxid not in self.config.get("gpt4") else self.system_content_msg2,
                {"role": "system", "content": "" + time_mk + now_time}
            ]
            self.conversation_list[wxid] = question_

        # 当前问题
        content_question_ = {"role": role, "content": question}
        self.conversation_list[wxid].append(content_question_)

        for cont in self.conversation_list[wxid]:
            if cont["role"] != "system":
                continue
            if cont["content"].startswith(time_mk):
                cont["content"] = time_mk + now_time

        # 只存储10条记录，超过滚动清除
        i = len(self.conversation_list[wxid])
        if i > 5:
            self.LOG.info("滚动清除微信记录：%s", wxid)
            # 删除多余的记录，倒着删，且跳过第一个的系统消息
            del self.conversation_list[wxid][1]


if __name__ == "__main__":
    LOG = logging.getLogger("chatgpt")
    config: dict = Config().LLM_BOT
    if not config:
        LOG.info("chatgpt配置丢失, 测试运行失败")
        exit(0)
    chat = ChatGPT()
    # 测试程序
    while True:
        q = input(">>> ")
        try:
            time_start = datetime.now()  # 记录开始时间
            LOG.info(chat.get_answer(q, "wxid_tqn5yglpe9gj21", "wxid_tqn5yglpe9gj21"))
            time_end = datetime.now()  # 记录结束时间
            LOG.info(f"{round((time_end - time_start).total_seconds(), 2)}s")  # 计算的时间差为程序的执行时间，单位为秒/s
        except Exception as e:
            LOG.error(e)
