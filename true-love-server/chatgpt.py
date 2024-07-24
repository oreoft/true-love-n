#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import base64
import concurrent
import json
import logging
import os
import random
import time
from concurrent import futures
from datetime import datetime

import requests

import base_client
import context_vars
from configuration import Config

executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

name = "chatgpt"


def get_file_path(msg_id):
    project_directory = os.path.dirname(os.path.abspath(__file__))
    download_directory = project_directory + '/sd-jpg/'
    # 构建唯一文件名
    local_filename = f'{msg_id if msg_id else str(time.time())}.jpg'
    # 构建完整的文件路径
    return os.path.join(download_directory, local_filename)


# 抽象接口
class ChatBot:
    def get_answer(self, question: str, wxid: str, sender: str) -> str:
        pass


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
            rsp = {"type": "chat", "answer": "ai服务正在发版, 稍后再试试捏"}
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
            # 获取结果
            rsp = response.json().get('data') or response.json().get('message')
        except Exception as e0:
            self.LOG.error("发送到sd出错", e0)
            rsp = '发生未知错误, 稍后再试试捏'
        return rsp

    def get_img_type(self, question, not_img):
        try:
            # 准备数据
            data = {
                "token": self.token,
                "content": question,
                "not_img": not_img,
            }

            # 请求配置
            url = 'http://notice.someget.work/get-img-type'
            headers = {'Content-Type': 'application/json'}

            # 发送请求
            start_time = time.time()
            self.LOG.info("开始发送给get_img_type")
            response = requests.post(url, headers=headers, data=json.dumps(data))
            # 获取结果
            rsp = response.json().get('data') or response.json().get('message')
            self.LOG.info(f"get_answer_type回答时间为：{round(time.time() - start_time, 2)}s, result:{rsp}")
        except Exception as e0:
            self.LOG.error("发送到sd出错", e0)
            rsp = '发生未知错误, 稍后再试试捏'
        return rsp

    def send_analyze(self, question, wxid, sender, img_path):
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
            url = 'http://notice.someget.work/get-analyze'
            headers = {'Content-Type': 'application/json'}

            # 发送请求
            response = requests.post(url, headers=headers, data=json.dumps(data))
            # 获取结果
            rsp = response.json().get('data') or response.json().get('message')
        except Exception as e0:
            self.LOG.error("发送到send_analyze出错", e0)
            rsp = '发生未知错误, 稍后再试试捏'
        return rsp

    def get_answer_type(self, question: str, wxid: str, sender: str):
        start_time = time.time()
        self.LOG.info("开始发送给get_answer_type")
        rsp = self.send_chatgpt(question, wxid, sender)
        # 判断gpt分析的结果
        result = json.loads(rsp)
        end_time = time.time()
        cost = round(end_time - start_time, 2)
        self.LOG.info(f"get_answer_type回答时间为：{cost}s, result:{result}")
        result["ioCost"] = cost
        return result

    def get_answer(self, question: str, wxid: str, sender: str):
        # 处理固定返回的情况
        rsp = process_ban(sender)
        if rsp != '':
            base_client.send_text(wxid, sender, rsp)
            return ''
        # 开始走ai
        result = self.get_answer_type(question, wxid, sender)
        if 'type' in result and result['type'] == 'gen-img':
            return self.async_gen_img(f"user_input:{question}, supplementary:{result['answer']}", wxid, sender)
        if 'answer' in result:
            rsp = result['answer']
        if 'debug' in result:
            rsp = rsp + '\n\n' + str(result['debug']).replace('$', str(result['ioCost']))
        base_client.send_text(wxid, sender, rsp)

    def async_get_answer(self, question: str, wxid: str, sender: str) -> str:
        # 这里异步调用方法
        executor.submit(self.get_answer, question, wxid, sender)
        # 这里先固定回复
        return ""

    def async_gen_img(self, question: str, wxid: str, sender: str) -> str:
        # 这里异步调用方法
        executor.submit(self.gen_img, question, wxid, sender, '', context_vars.local_msg_id.get(''))
        # 这里先固定回复
        base_client.send_text(wxid, sender, "🚀您的作品将在1~10分钟左右完成，请耐心等待")
        return ""

    def async_gen_img_by_img(self, question: str, img_path: str, wxid: str, sender: str) -> str:
        result = json.loads(self.get_img_type(question, not img_path))
        if 'type' in result and result['type'] == 'analyze_img':
            executor.submit(self.gen_analyze, question, wxid, sender, img_path)
            base_client.send_text(wxid, sender, "🔍让我仔细瞧瞧，请耐心等待")
            return ""
        # 其他都是改图
        executor.submit(self.gen_img, result, wxid, sender, img_path, context_vars.local_msg_id.get(''))
        # 这里先固定回复
        base_client.send_text(wxid, sender, "🚀您的作品将在1~10分钟左右完成，请耐心等待")
        return ""

    def gen_img(self, question, wxid, sender, img_path='', msg_id=''):
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
        file_path = get_file_path(msg_id)
        # 将解码后的图像数据写入文件
        with open(file_path, "wb") as file:
            file.write(base64.b64decode(rsp.get('img')))
        base_client.send_img(file_path, wxid)

    def gen_analyze(self, question, wxid, sender, img_path=''):
        start_time = time.time()
        self.LOG.info(f"开始发送给gen_analyze分析, img_path={img_path[:10]}")
        rsp = self.send_analyze(question, wxid, sender, img_path)
        end_time = time.time()
        cost = round(end_time - start_time, 2)
        self.LOG.info("gen_analyze回答时间为：%s 秒", cost)
        base_client.send_text(wxid, sender, rsp)


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


def process_ban(sender):
    if sender == 'Dante516':
        advice_list = [
            "大野猫,我们应该尊重这个群体,避免发送任何令人反感的言论。",
            "大野猫哥,那种言语可能会冒犯或伤害他人,希望你能三思而行。",
            "我理解每个人都有自己的私密空间,但请不要在公共场合发这种内容。",
            "作为群友,我建议你寻求专业的心理咨询,释放内心的压力。",
            "让我们共同维护这个群体的和谐氛围,互相尊重。",
            "这种言语可能会给人一种性骚扰的感觉,我希望大野猫哥你能改正。",
            "我相信大野猫是一个善良的人,只是暂时失去了分寸。",
            "用文字表达想法时,请三思而后行,避免伤害他人。",
            "作为朋友,我愿意倾听你的烦恼,但请不要以这种方式发泄。",
            "让我们携手共创一个积极向上、互相尊重的良好环境。"
        ]
        return random.choice(advice_list)
    return ''


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
