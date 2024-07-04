#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import base64
import concurrent
import json
import logging
import os
import time
from concurrent import futures
from datetime import datetime

import requests

import base_client
import context_vars
from configuration import Config
from msg_handler import ChatBot

executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

name = "chatgpt"


def get_file_path():
    project_directory = os.path.dirname(os.path.abspath(__file__))
    download_directory = project_directory + '/sd-jpg/'
    # 构建唯一文件名
    local_filename = f'{context_vars.local_msg_id.get(str(time.time()))}.jpg'
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

    def send_sd(self, question, wxid, sender, img_path):
        try:
            # 准备数据
            data = {
                "token": self.token,
                "content": question,
                'wxid': wxid,
                "sender": sender,
                "img_path": image_to_base64(img_path),
            }

            # 请求配置
            url = 'http://notice.someget.work/gen-img'
            headers = {'Content-Type': 'application/json'}

            # 发送请求
            response = requests.post(url, headers=headers, data=json.dumps(data))
            self.LOG.info(response.text)
            self.LOG.info(response.json())
            # 获取结果
            rsp = response.json().get('data') or response.json().get('message')
        except Exception as e0:
            self.LOG.error("发送到sd出错", e0)
            rsp = '发生未知错误, 稍后再试试捏'
        return rsp

    def get_answer(self, question: str, wxid: str, sender: str):
        start_time = time.time()
        self.LOG.info("开始发送给chatgpt")
        rsp = self.send_chatgpt(question, wxid, sender)
        # 判断gpt分析的结果
        result = json.loads(rsp)
        end_time = time.time()
        cost = round(end_time - start_time, 2)
        self.LOG.info("chat回答时间为：%s 秒", cost)
        if 'type' in result and result['type'] == 'gen-img':
            return self.async_gen_img(f"user_input:{question}, supplementary:{result['answer']}", wxid, sender)
        if 'answer' in result:
            rsp = result['answer']
        if 'debug' in result:
            rsp = rsp + '\n\n' + str(result['debug']).replace('$', str(cost))
        base_client.send_text(wxid, sender, rsp)

    def async_get_answer(self, question: str, wxid: str, sender: str) -> str:
        # 这里异步调用方法
        executor.submit(self.get_answer, question, wxid, sender)
        # 这里先固定回复
        return ""

    def async_gen_img(self, question: str, wxid: str, sender: str) -> str:
        # 这里异步调用方法
        executor.submit(self.gen_img, question, wxid, sender, '')
        # 这里先固定回复
        base_client.send_text(wxid, sender, "🚀您的作品将在1~10分钟左右完成，请耐心等待")
        return ""

    def async_gen_img_by_img(self, question: str, img_path: str, wxid: str, sender: str) -> str:
        # 这里异步调用方法
        executor.submit(self.gen_img, question, wxid, sender, img_path)
        # 这里先固定回复
        base_client.send_text(wxid, sender, "🚀您的作品将在1~10分钟左右完成，请耐心等待")
        return ""

    def gen_img(self, question, wxid, sender, img_path=''):
        start_time = time.time()
        self.LOG.info(f"开始发送给sd生图, img_path={img_path[:10]}")
        rsp = self.send_sd(question, wxid, sender, img_path)
        end_time = time.time()
        cost = round(end_time - start_time, 2)
        self.LOG.info("sd回答时间为：%s 秒", cost)
        if 'prompt' not in rsp:
            base_client.send_text(wxid, sender, rsp)
            return

        res_text = f"🎨绘画完成! \nprompt: {rsp.get('prompt')}"
        base_client.send_text(wxid, sender, res_text)

        # 获取当前脚本所在的目录，即项目目录
        file_path = get_file_path()
        # 将解码后的图像数据写入文件
        with open(file_path, "wb") as file:
            file.write(base64.b64decode(rsp.get('img')))
        base_client.send_img(file_path, wxid)


def image_to_base64(image_path):
    """
    将图片文件转换为Base64编码的字符串。

    :param image_path: 图片文件的路径
    :return: Base64编码的字符串
    """
    if image_path:
        with open(image_path, "rb") as image_file:
            # 读取文件内容
            encoded_string = base64.b64encode(image_file.read())
            return encoded_string.decode('utf-8')
    return ""


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
