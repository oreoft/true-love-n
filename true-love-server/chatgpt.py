#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import base64
import json
import logging
import os
import time
from datetime import datetime

import requests

import base_client
from configuration import Config
from msg_handler import ChatBot

name = "chatgpt"


def get_file_path(sender):
    project_directory = os.path.dirname(os.path.abspath(__file__))
    download_directory = project_directory + '/sd-jpg/'
    # 构建唯一文件名
    local_filename = f'{sender}-{str(time.time())}.jpg'
    # 构建完整的文件路径
    return os.path.join(download_directory, local_filename)


class ChatGPT(ChatBot):

    def __init__(self) -> None:
        self.LOG = logging.getLogger("MsgHandler")
        self.token: dict = Config().HTTP_TOKEN

    def send_chatgpt(self, question, wxid, sender):
        try:
            # 准备数据
            data = {
                "token": self.token,
                "content": question,
                'wxid': wxid,
                "sender": sender,
            }

            # 请求配置
            url = 'http://notice.someget.work/get-llm'
            headers = {'Content-Type': 'application/json'}

            # 发送请求
            response = requests.post(url, headers=headers, data=json.dumps(data))

            # 获取结果
            rsp = response.json().get('data') or response.json().get('message')
        except Exception as e0:
            self.LOG.error("发送到chatgpt出错", e0)
            rsp = '发生未知错误, 稍后再试试捏'
        return rsp

    def send_sd(self, question, wxid, sender):
        try:
            # 准备数据
            data = {
                "token": self.token,
                "content": question,
                'wxid': wxid,
                "sender": sender,
            }

            # 请求配置
            url = 'http://notice.someget.work/gen-img'
            headers = {'Content-Type': 'application/json'}

            # 发送请求
            response = requests.post(url, headers=headers, data=json.dumps(data))
            # 获取结果
            rsp = response.json().get('data') or response.json().get('message')
        except Exception as e0:
            self.LOG.error("发送到sd出错", e0)
            rsp = '发生未知错误, 稍后再试试捏'
        return rsp

    def get_answer(self, question: str, wxid: str, sender: str) -> str:
        start_time = time.time()
        self.LOG.info("开始发送给chatgpt")
        rsp = self.send_chatgpt(question, wxid, sender)
        end_time = time.time()
        cost = round(end_time - start_time, 2)
        self.LOG.info("chat回答时间为：%s 秒", cost)
        return rsp

    def gen_img(self, question: str, wxid: str, sender: str) -> str:
        start_time = time.time()
        # 这里异步调用方法
        # 尝试获取当前事件循环
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # 创建一个新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # 如果事件循环正在运行，创建并安排一个任务，但不等待它
            loop.create_task(self.async_gen_img(question, sender, start_time, wxid))
        else:
            print("不在事件循环里面,启用run_until_complete同步")
            loop.run_until_complete(self.async_gen_img(question, sender, start_time, wxid))
        # 这里先固定回复
        return "🚀您的作品将在1~10分钟左右完成，请耐心等待"

    async def async_gen_img(self, question, sender, start_time, wxid):
        self.LOG.info("开始发送给sd生图")
        rsp = self.send_sd(question, wxid, sender)
        end_time = time.time()
        cost = round(end_time - start_time, 2)
        self.LOG.info("sd回答时间为：%s 秒", cost)
        res_text = f"🎨绘画完成! \n prompt: {rsp.get('prompt')}"
        base_client.send_text(wxid, sender, res_text)

        # 获取当前脚本所在的目录，即项目目录
        file_path = get_file_path(sender)
        # 将解码后的图像数据写入文件
        with open(file_path, "wb") as file:
            file.write(base64.b64decode(rsp.get('img')))
        base_client.send_img(file_path, wxid)


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
            LOG.info(chat.gen_img(q, "", ""))
            time_end = datetime.now()  # 记录结束时间
            LOG.info(f"{round((time_end - time_start).total_seconds(), 2)}s")  # 计算的时间差为程序的执行时间，单位为秒/s
        except Exception as e:
            LOG.error(e)
