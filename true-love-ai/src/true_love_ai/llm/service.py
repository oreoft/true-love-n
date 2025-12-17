#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 服务模块
支持多种大语言模型（OpenAI、Claude、DeepSeek）
提供对话管理、图像分析等功能
"""
import json
import logging
import time
from datetime import datetime

import litellm
from litellm import Router

from true_love_ai.configuration import Config
from true_love_ai.llm.constants import (
    OPENAI_MODEL, OPENAI_VISION_MODEL, CLAUDE_MODEL, DEEPSEEK_MODEL,
    DEFAULT_MODEL, MAX_CONVERSATION_LENGTH
)
from true_love_ai.llm.function_calls import TYPE_ANSWER_CALL, IMG_TYPE_ANSWER_CALL
from true_love_ai.services.search_service import fetch_baidu_references
from true_love_ai.services.image_service import ImageService

# 模块名称（用于配置识别）
name = "chatgpt"

# LiteLLM 配置
litellm.modify_params = True
litellm.drop_params = True


def fetch_stream(ret, is_function_call: bool = False) -> str:
    """
    处理流式响应
    
    Args:
        ret: 流式响应对象
        is_function_call: 是否为 function call 响应
        
    Returns:
        拼接后的响应字符串
    """
    rsp = ''
    for stream_res in ret:
        try:
            if is_function_call:
                # 处理函数/工具调用
                if stream_res.choices[0].delta.tool_calls:
                    tool_call = stream_res.choices[0].delta.tool_calls[0]
                    if tool_call.function.arguments:
                        rsp += tool_call.function.arguments.replace('\n\n', '\n')
            else:
                # 处理普通文本内容
                if stream_res.choices[0].delta.content:
                    rsp += stream_res.choices[0].delta.content.replace('\n\n', '\n')
        except Exception as e:
            logging.debug(f"处理流式响应时出错: {e}")
            continue
    return rsp


class LLMService:
    """
    大语言模型服务
    支持 OpenAI、Claude、DeepSeek 等多种模型
    """

    def __init__(self) -> None:
        self.LOG = logging.getLogger("LLMService")
        self.config = Config().LLM_BOT
        self.current_model = DEFAULT_MODEL
        
        # 初始化路由器（支持多 API Key 负载均衡）
        self.router = self._init_router()
        
        # 对话历史容器
        self.conversation_list = {}
        
        # 加载系统提示词
        self._load_prompts()
        
        # 图像服务
        self.image_service = ImageService()

    def _init_router(self) -> Router:
        """初始化 LiteLLM 路由器"""
        model_list = [
            # OpenAI 多 Key 配置 (GPT-5 不支持自定义 temperature，只能用 temperature=1)
            {"model_name": OPENAI_MODEL, "litellm_params": {"model": OPENAI_MODEL, "api_key": self.config.get('key1'), "temperature": 1}},
            {"model_name": OPENAI_MODEL, "litellm_params": {"model": OPENAI_MODEL, "api_key": self.config.get('key2'), "temperature": 1}},
            {"model_name": OPENAI_MODEL, "litellm_params": {"model": OPENAI_MODEL, "api_key": self.config.get('key3'), "temperature": 1}},
            # Claude
            {"model_name": CLAUDE_MODEL, "litellm_params": {"model": CLAUDE_MODEL, "api_key": self.config.get('claude_key1')}},
            # DeepSeek
            {"model_name": DEEPSEEK_MODEL, "litellm_params": {"model": DEEPSEEK_MODEL, "api_key": self.config.get('ds_key1')}},
        ]
        return Router(model_list=model_list)

    def _load_prompts(self) -> None:
        """加载系统提示词"""
        self.prompts = {
            'default': {"role": "system", "content": self.config.get("prompt", "")},
            'gpt4': {"role": "system", "content": self.config.get("prompt2", "")},
            'xunwen': {"role": "system", "content": self.config.get("prompt3", "")},
            'img_prompt': {"role": "system", "content": self.config.get("prompt4", "")},
            'img_type': {"role": "system", "content": self.config.get("prompt5", "")},
            'img_analyze': {"role": "system", "content": self.config.get("prompt6", "")},
        }

    # ==================== 核心对话方法 ====================
    
    def get_answer(self, question: str, wxid: str, sender: str) -> dict:
        """
        获取聊天回答（主入口）
        
        Args:
            question: 用户问题
            wxid: 用户标识
            sender: 发送者
            
        Returns:
            {"type": str, "answer": str, "debug": str(可选)}
        """
        clean_question = question.replace("debug", "", 1) if question else '你好'
        self._update_message(wxid, clean_question, "user")
        
        start_time = time.time()
        self.LOG.info(f"开始调用 LLM, model: {self.current_model}")
        
        rsp = self._send_chat_request(self.current_model, wxid)
        
        cost = round(time.time() - start_time, 2)
        self.LOG.info(f"回答耗时: {cost}s")
        
        if question.startswith('debug'):
            rsp['debug'] = f"(aiCost: {cost}s, model: {self.current_model})"
        
        return rsp

    def _send_chat_request(self, model: str, wxid: str) -> dict:
        """
        发送聊天请求
        
        Args:
            model: 使用的模型
            wxid: 用户标识
            
        Returns:
            {"type": str, "answer": str}
        """
        try:
            question = self.conversation_list[wxid][-1]
            
            # 先判断消息类型
            ret = self.router.completion(
                model=model,
                messages=self.conversation_list[wxid],
                tool_choice={"type": "function", "function": {"name": "type_answer"}},
                tools=TYPE_ANSWER_CALL,
                stream=True
            )
            
            rsp_str = fetch_stream(ret, True)
            result = json.loads(rsp_str)
            self.LOG.info(f"LLM 类型判断结果: {result}")
            
            # 如果需要搜索，执行搜索增强
            if result['type'] == 'search':
                result = self._handle_search_request(model, wxid, question, result)
            
            self._update_message(wxid, rsp_str, "assistant")
            return result
            
        except Exception as e:
            self.LOG.exception(f"调用 LLM 服务出错: {e}")
            return {"type": "chat", "answer": "发生未知错误, 稍后再试试捏"}

    def _handle_search_request(self, model: str, wxid: str, question: dict, result: dict) -> dict:
        """处理搜索请求"""
        # 获取百度搜索结果
        reference_list = fetch_baidu_references(result['answer'])
        self.LOG.info(f"搜索结果数量: {len(reference_list)}")
        
        # 构建搜索增强 prompt
        refer_prompt = {
            "role": "assistant",
            "content": f"针对这个回答, 参考信息和来源链接如下: {json.dumps(reference_list)}"
        }
        search_system_prompt = {
            "role": "system",
            "content": (
                "下面你的回答必须结合上下文,因为上下文都是联网查询的,尤其是assistant的来源和参考链接，"
                "所以相当于你可以联网获取信息, 所以不允许说你不能联网, "
                "如果assistant的参考是一个空list, 你就说联网查询超时了, 引导用户再问一遍"
                "另外如果你不知道回答，请不要不要胡说. "
                "如果用户要求文章或者链接请你把最相关的参考链接给出(参考链接必须在上下文出现过)"
            )
        }
        
        # 再次调用 LLM 生成回答
        ret = self.router.completion(
            model=model,
            messages=self.conversation_list[wxid] + [refer_prompt, search_system_prompt, question],
            stream=True
        )
        
        rsp_str = fetch_stream(ret)
        search_tail = f"\n- - - - - - - - - - - -\n\n🐾💩🕵：{result['answer']}"
        
        return {"type": "chat", "answer": self._extract_answer(rsp_str) + search_tail}

    # ==================== 图像相关方法 ====================
    
    def get_analyze_by_img(self, content: str, img_data: str, wxid: str) -> str:
        """
        分析图像内容
        
        Args:
            content: 用户问题
            img_data: base64 编码的图像
            wxid: 用户标识
            
        Returns:
            分析结果文本
        """
        clean_content = content.replace("debug", "", 1)
        self._update_message(wxid, clean_content, "user")
        
        try:
            start_time = time.time()
            self.LOG.info("开始分析图像")
            
            ret = self.router.completion(
                model=OPENAI_VISION_MODEL,
                messages=[
                    self.prompts['img_analyze'],
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": content},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_data}"}}
                        ]
                    }
                ],
                stream=True
            )
            
            cost = round(time.time() - start_time, 2)
            self.LOG.info(f"图像分析耗时: {cost}s")
            
            result = fetch_stream(ret)
            self._update_message(wxid, result, "assistant")
            
            if content.startswith('debug'):
                result = f"{result}\n\n(aiCost: {cost}s, model: {OPENAI_VISION_MODEL})"
            
            return result
            
        except Exception:
            self.LOG.exception("图像分析错误")
            raise

    def get_img_type(self, content: str) -> str:
        """
        判断图像操作类型并生成描述词
        
        Args:
            content: 用户描述
            
        Returns:
            JSON 字符串 {"type": str, "answer": str}
        """
        try:
            start_time = time.time()
            self.LOG.info("开始判断图像操作类型")
            
            result = self._send_message(
                messages=[self.prompts['img_type'], {"role": "user", "content": content}],
                function_call={"type": "function", "function": {"name": "img_type_answer_call"}},
                functions=IMG_TYPE_ANSWER_CALL,
            )
            
            self.LOG.info(f"类型判断耗时: {(time.time() - start_time) * 1000:.0f}ms, result: {result}")
            return result
            
        except Exception:
            self.LOG.exception("判断图像类型错误")
            raise

    def get_img(self, content: str) -> dict:
        """
        根据文字描述生成图像
        
        Args:
            content: 用户描述
            
        Returns:
            {"prompt": str, "img": base64_str}
        """
        # 先生成图像描述词
        try:
            start_time = time.time()
            self.LOG.info("开始生成图像描述词")
            
            image_prompt = self._send_message(
                messages=[self.prompts['img_prompt'], {"role": "user", "content": content}]
            )
            
            self.LOG.info(f"描述词生成耗时: {(time.time() - start_time) * 1000:.0f}ms")
        except Exception:
            self.LOG.exception("生成图像描述词错误")
            image_prompt = content
        
        # 调用图像服务生成图像
        return self.image_service.generate_image(image_prompt)

    def get_img_by_img(self, content: dict, img_data: str) -> dict:
        """
        根据图像生成/编辑图像
        
        Args:
            content: {"type": str, "answer": str}
            img_data: base64 编码的原图
            
        Returns:
            {"prompt": str, "img": base64_str}
        """
        return self.image_service.edit_image(
            img_data=img_data,
            operation_type=content["type"],
            prompt=content["answer"]
        )

    # ==================== 特殊功能方法 ====================
    
    def get_xun_wen(self, question: str) -> str:
        """
        询问功能（特定格式问题）
        
        Args:
            question: 格式为 "xxx-实际问题"
            
        Returns:
            回答文本
        """
        content = question.split("-")[1]
        return self._send_message([self.prompts['xunwen'], {"role": "user", "content": content}])

    # ==================== 工具方法 ====================
    
    def _send_message(self, messages: list, function_call=None, functions=None) -> str:
        """
        发送消息到 LLM
        
        Args:
            messages: 消息列表
            function_call: function call 配置
            functions: functions 定义
            
        Returns:
            响应字符串
        """
        try:
            ret = self.router.completion(
                model=self.current_model,
                messages=messages,
                tool_choice=function_call,
                tools=functions,
                stream=True
            )
            return fetch_stream(ret, functions is not None)
        except Exception as e:
            self.LOG.error(f"发送消息错误: {e}")
            return "An unknown error has occurred. Try again later."

    def _update_message(self, wxid: str, content: str, role: str) -> None:
        """
        更新对话历史
        
        Args:
            wxid: 用户标识
            content: 消息内容
            role: 角色（user/assistant）
        """
        time_mk = (
            f"当需要回答当前时间或者关于当前日期类问题, 请直接参考这个时间: "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            f"(请注意这是美国中部时间, 你可以告诉别人你使用的时区), "
            f"另外用户提升是否可以联网你需要说我已经接入谷歌搜索, "
            f"并且知识库最新消息是: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # 初始化对话历史
        if wxid not in self.conversation_list:
            # 根据用户选择不同的系统 prompt
            system_prompt = (
                self.prompts['gpt4'] 
                if wxid in self.config.get("gpt4", []) 
                else self.prompts['default']
            )
            self.conversation_list[wxid] = [
                system_prompt,
                {"role": "system", "content": time_mk}
            ]
        
        # 添加当前消息
        self.conversation_list[wxid].append({"role": role, "content": content})
        
        # 刷新时间
        self.conversation_list[wxid][1] = {"role": "system", "content": time_mk}
        
        # 滚动清除超出限制的历史
        if len(self.conversation_list[wxid]) > MAX_CONVERSATION_LENGTH:
            self.LOG.info(f"滚动清除聊天记录: {wxid}")
            del self.conversation_list[wxid][2]

    @staticmethod
    def _extract_answer(rsp_str: str) -> str:
        """从响应中提取 answer 字段（如果是 JSON 格式）"""
        try:
            data = json.loads(rsp_str)
            if isinstance(data, dict) and 'answer' in data:
                return data['answer']
        except json.JSONDecodeError:
            pass
        return rsp_str


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    LOG = logging.getLogger("llm_service")
    
    config = Config().LLM_BOT
    if not config:
        LOG.info("LLM 配置丢失, 测试运行失败")
        exit(0)
    
    llm = LLMService()
    
    # 测试程序
    while True:
        q = input(">>> ")
        try:
            time_start = datetime.now()
            LOG.info(llm.get_answer(q, "", ""))
            time_end = datetime.now()
            LOG.info(f"{round((time_end - time_start).total_seconds(), 2)}s")
        except Exception as e:
            LOG.error(e)
