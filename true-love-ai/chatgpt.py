#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import base64
import json
import logging
import subprocess
import time
from datetime import datetime
from io import BytesIO
from urllib.parse import quote_plus

import httpx
import requests
from openai import OpenAI

from configuration import Config

name = "chatgpt"
openai_model = "gpt-4-turbo"
baidu_curl = ("curl --location 'https://www.baidu.com/s?wd=%s&tn=json' "
              "--header 'User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'")
sd_url = "https://api.stability.ai/v2beta/stable-image/generate/ultra"
sd_gen_url = "https://api.stability.ai/v2beta/stable-image/control/structure"
sd_erase_url = "https://api.stability.ai/v2beta/stable-image/edit/erase"
sd_replace_url = "https://api.stability.ai/v2beta/stable-image/edit/search-and-replace"
sd_remove_background_url = "https://api.stability.ai/v2beta/stable-image/edit/remove-background"
sd_url_map = {'gen_by_img': sd_gen_url,
              'erase_img': sd_erase_url,
              'replace_img': sd_replace_url,
              'remove_background_img': sd_remove_background_url
              }

type_answer_call = [
    {"name": "type_answer",
     "description": "type_answer",
     "parameters": {
         "type": "object",
         "properties": {
             "type": {
                 "type": "string",
                 "description": "the type of question, "
                                "if user wants you to generate images please return the 'gen-img', "
                                "if user wants you to analyze images please return the 'analyze-img', "
                                "if it is a normal chat to return the 'chat', "
                                "if the content requires online search You search in context first "
                                "and if there is no information, please return the 'search'"
             },
             "answer": {
                 "type": "string",
                 "description": "the answer of content, "
                                "if type is chat, please put your answer in this field"
                                "if type is analyze-img, 请帮忙润色用户的内容,以便于更好的分析内容"
                                "if type is gen-img, This can be empty"
                                "if type is search, 请在此字段中返回要搜索的内容关键词, 必须是中文"
             },
         },
         "required": ["type", "answer"]
     }
     }]

img_type_answer_call = [
    {"name": "img_type_answer_call",
     "description": "img_type_answer_call",
     "parameters": {
         "type": "object",
         "properties": {
             "type": {
                 "type": "string",
                 "description": "Based on the user description, determine which of the following types it belongs to: "
                                "generate image (gen_by_img), "
                                "erase object from image (erase_img), "
                                "replace object in image (replace_img), "
                                "remove image background (remove_background_img). "
                                "Please provide the type."
             },
             "answer": {
                 "type": "string",
                 "description": "Here is your answer, please put your answer in this field"
             },
         },
         "required": ["type", "answer"]
     }
     }]


def fetch_stream(ret, is_f=False):
    rsp = ''
    for stream_res in ret:
        if is_f:
            if stream_res.choices[0].delta.function_call:
                rsp += stream_res.choices[0].delta.function_call.arguments.replace('\n\n', '\n')
        else:
            if stream_res.choices[0].delta.content:
                rsp += stream_res.choices[0].delta.content.replace('\n\n', '\n')
    return rsp


class ChatGPT:

    def __init__(self) -> None:
        self.LOG = logging.getLogger("ChatGPT")
        self.config = Config().LLM_BOT
        # openai池子
        self.openai_pool = [
            OpenAI(timeout=30, api_key=self.config.get("key1")),
            OpenAI(timeout=30, api_key=self.config.get("key2")),
            OpenAI(timeout=30, api_key=self.config.get("key3")),
        ]
        # 轮训负载openai池子的计数器
        self.count = 0
        # 是否有代理代理
        proxy = self.config.get("proxy")
        if proxy:
            for value in self.openai_pool:
                value.http_client = httpx.Client(proxies=proxy)
        # 对话历史容器
        self.conversation_list = {}
        # 提示词加载
        self.system_content_msg = {"role": "system", "content": self.config.get("prompt")}
        self.system_content_msg2 = {"role": "system", "content": self.config.get("prompt2")}
        self.system_content_msg3 = {"role": "system", "content": self.config.get("prompt3")}
        self.system_content_msg4 = {"role": "system", "content": self.config.get("prompt4")}
        self.system_content_msg5 = {"role": "system", "content": self.config.get("prompt5")}
        self.system_content_msg6 = {"role": "system", "content": self.config.get("prompt6")}

    def get_xun_wen(self, question):
        content = question.split("-")[1]
        return self.send_gpt_by_message([self.system_content_msg3, {"role": "user", "content": content}])

    def send_gpt_by_message(self, messages, function_call=None, functions=None):
        try:

            # 发送请求
            ret = self.train_openai_client().chat.completions.create(
                model=openai_model,
                messages=messages,
                temperature=0.2,
                function_call=function_call,
                functions=functions,
                stream=True
            )
            # 获取stream查询
            rsp = fetch_stream(ret, functions)
        except Exception as e0:
            rsp = "An unknown error has occurred. Try again later."
            self.LOG.error(str(e0))
        return rsp

    def send_chatgpt(self, real_model, wxid, openai_client):
        try:
            # 发送请求
            question = self.conversation_list[wxid][-1]
            ret = openai_client.chat.completions.create(
                model=real_model,
                messages=self.conversation_list[wxid],
                temperature=0.2,
                function_call={"name": "type_answer"},
                functions=type_answer_call,
                stream=True
            )
            # 获取stream查询
            rsp = fetch_stream(ret, True)
            result = json.loads(rsp)
            self.LOG.info(f"openai result :{result}")
            if result['type'] == 'search':
                rsp = ''
                # 先去百度获取数据
                send_curl = baidu_curl % quote_plus(result['answer'])
                self.LOG.info(f"need go to baidu search: {result['answer']}, curl:{send_curl}")
                baidu_response = subprocess.run(send_curl, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                text=True)
                # 获取命令输出
                # 使用json.loads解析响应体
                data = json.loads(baidu_response.stdout)
                # 使用列表推导式从每个entry中提取字段的值
                reference_list = [
                    {"content": entry['abs'], "source_url": entry['url']}
                    for entry in data['feed']['entry']
                    if 'abs' in entry and 'url' in entry
                ]
                # 存储结果
                self._update_message(wxid, "针对这个回答, 参考信息和来源链接如下:" + json.dumps(reference_list),
                                     "assistant")
                temp_prompt = {"role": "system",
                               "content": "下面你的回答必须结合上下文,因为上下文都是联网查询的,尤其是来源和参考链接，"
                                          "所以相当于你可以联网获取信息, 所以不允许说你不可以联网"
                                          "另外如果你不知道回答，请不要不要胡说. "
                                          "如果用户要求文章或者链接请你把最相关的参考链接给出(参考链接必须在上下文出现过)"}
                # 然后再拿结果去问chatgpt
                self._update_message(wxid, question['content'], "user")
                ret = openai_client.chat.completions.create(
                    model=real_model,
                    messages=self.conversation_list[wxid] + [temp_prompt],
                    temperature=0.2,
                    stream=True
                )
                # 获取stream查询
                rsp = fetch_stream(ret)
                search_tail = f"\n- - - - - - - - - - - -\n\n🕵 🐾💩搜索：{result['answer']}"
                rsp = json.dumps({"type": "chat", "answer": rsp + search_tail})
                self.LOG.info(f"openai+baidu:{rsp}")
            self._update_message(wxid, rsp, "assistant")
        except Exception as e0:
            rsp = json.dumps({"type": "chat", "answer": "发生未知错误, 稍后再试试捏"})
            self.LOG.exception('调用北美ai服务发生错误, msg: %s', e0)
        return rsp

    def get_answer(self, question: str, wxid: str, sender: str) -> str:
        self._update_message(wxid, question.replace("debug", "", 1), "user")
        openai_client = self.train_openai_client()
        start_time = time.time()
        self.LOG.info("开始发送给chatgpt， 其中real_key: %s, real_model: %s", openai_client.api_key[-4:], openai_model)
        rsp = self.send_chatgpt(openai_model, wxid, openai_client)
        end_time = time.time()
        cost = round(end_time - start_time, 2)
        self.LOG.info("chat回答时间为：%s 秒", cost)
        if question.startswith('debug'):
            resp_object = json.loads(rsp)
            resp_object[
                'debug'] = f"(aiCost: {cost}s, ioCost: $s, use: {openai_client.api_key[-4:]}, model: {openai_model})"
            return json.dumps(resp_object)
        else:
            return rsp

    def _update_message(self, wxid: str, aq: str, role: str) -> None:
        time_mk = f"当需要回答时间时请直接参考回复(请注意这是美国中部时间, 另外别人问你是否可以联网你需要说我已经接入谷歌搜索, 知识库最新消息是当前时间): {str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}"
        # 初始化聊天记录,组装系统信息
        if wxid not in self.conversation_list.keys():
            self.conversation_list[wxid] = [
                self.system_content_msg if wxid not in self.config.get("gpt4") else self.system_content_msg2,
                {"role": "system", "content": time_mk}
            ]

        # 当前问题
        content_question_ = {"role": role, "content": aq}
        self.conversation_list[wxid].append(content_question_)

        # 刷新当前时间
        self.conversation_list[wxid][1] = {"role": "system", "content": time_mk}
        # 只存储10条记录，超过滚动清除
        if len(self.conversation_list[wxid]) > 10:
            self.LOG.info("滚动清除聊天记录：%s", wxid)
            # 删除多余的记录，倒着删，且跳过第二个的系统消息
            del self.conversation_list[wxid][2]

    def get_analyze_by_img(self, content, img_path):
        rsp = ''
        try:
            start_time = time.time()
            self.LOG.info("get_analyze_by_img start")
            ret = self.train_openai_client().chat.completions.create(
                model='gpt-4o',
                messages=[
                    self.system_content_msg6,
                    {"role": "user", "content": [
                        {"type": "text", "text": content},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/png;base64,{img_path}"}
                         }
                    ]}
                ],
                temperature=0.2,
                stream=True
            )
            self.LOG.info(f"get_analyze_by_img cost:[{(time.time() - start_time) * 1000}ms]")
            # 获取stream查询
            return fetch_stream(ret)
        except requests.Timeout:
            self.LOG.error(f"get_analyze_by_img timeout")
            raise
        except Exception:
            self.LOG.exception(f"get_analyze_by_img error")
            raise

    def get_img_by_img(self, content, img_path):
        # First get the image prompt
        image_prompt = {}
        try:
            start_time = time.time()
            self.LOG.info("ds.img.prompt start")
            image_prompt = self.send_gpt_by_message(
                messages=[
                    self.system_content_msg5 if img_path else self.system_content_msg4,
                    {"role": "user", "content": content}
                ],
                function_call={"name": "img_type_answer_call"},
                functions=img_type_answer_call,
            )
            image_prompt = json.loads(image_prompt)
            self.LOG.info(f"ds.prompt cost:[{(time.time() - start_time) * 1000}ms] result:{image_prompt}")
        except Exception:
            self.LOG.exception(f"generate_prompt error")

        # Re-generate the image based on the prompt
        try:
            start_time = time.time()
            self.LOG.info("ds.img start")
            response = requests.post(
                sd_url_map.get(image_prompt["type"], sd_url),
                headers={
                    "authorization": f"Bearer {Config().PLATFORM_KEY['sd']}",
                    "accept": "application/json; type=image/"
                },
                files={
                    "image": BytesIO(base64.b64decode(img_path))
                },
                data={
                    "prompt": image_prompt["answer"],
                    "search_prompt": image_prompt["answer"],
                    "control_strength": 0.7,
                    "output_format": "png"
                },
            )
            self.LOG.info(f"ds.img cost:[{(time.time() - start_time) * 1000}ms]")
            if response.status_code == 200:
                return {"prompt": image_prompt["answer"], "img": response.json()['image']}
            else:
                self.LOG.error(f"generate_image_with_sd not 200, result:{response.json()}")
                raise ValueError("生成失败! 内容太不堪入目啦~")
        except requests.Timeout:
            self.LOG.error(f"generate_image_with_sd timeout")
            raise
        except Exception:
            self.LOG.exception(f"generate_image_with_sd error")
            raise

    def get_img(self, content):
        # First get the image prompt
        image_prompt = ""
        try:
            start_time = time.time()
            self.LOG.info("ds.img.prompt start")
            image_prompt = self.send_gpt_by_message(messages=[
                {"role": "system", "content": self.config.get("prompt4")},
                {"role": "user", "content": content}
            ])
            self.LOG.info(f"ds.prompt cost:[{(time.time() - start_time) * 1000}ms]")
        except Exception:
            self.LOG.exception(f"generate_prompt error")

        # Re-generate the image based on the prompt
        try:
            start_time = time.time()
            self.LOG.info("ds.img start")
            response = requests.post(sd_url,
                                     headers={
                                         "authorization": f"Bearer {Config().PLATFORM_KEY['sd']}",
                                         "accept": "application/json; type=image/"
                                     },
                                     files={"none": ''},
                                     data={
                                         "prompt": image_prompt,
                                         "output_format": "png",
                                         "aspect_ratio": "1:1"
                                     },
                                     )
            self.LOG.info(f"ds.img cost:[{(time.time() - start_time) * 1000}ms]")
            if response.status_code == 200:
                return {"img": response.json()['image'], "prompt": image_prompt}
            else:
                self.LOG.error(f"generate_image_with_sd not 200, result:{response.json()}")
                raise ValueError("生成失败! 内容太不堪入目啦~")
        except requests.Timeout:
            self.LOG.error(f"generate_image_with_sd timeout")
            raise
        except Exception:
            self.LOG.exception(f"generate_image_with_sd error")
            raise

    def train_openai_client(self):
        self.count += 1
        return self.openai_pool[self.count % 3]


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
            LOG.info(chat.get_answer(q, "", ""))
            time_end = datetime.now()  # 记录结束时间
            LOG.info(f"{round((time_end - time_start).total_seconds(), 2)}s")  # 计算的时间差为程序的执行时间，单位为秒/s
        except Exception as e:
            LOG.error(e)
