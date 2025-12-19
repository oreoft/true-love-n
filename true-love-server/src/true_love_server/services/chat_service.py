# -*- coding: utf-8 -*-
"""
Chat Service - 聊天服务

处理 AI 聊天相关的业务逻辑。
"""

import logging
import random

from . import base_client
from .ai_client import AIClient

LOG = logging.getLogger("ChatService")


def process_ban(sender: str) -> str:
    """处理被禁言用户的固定回复"""
    if sender == 'Dante516':
        advice_list = [
            "大野猫,我们应该尊重这个群体,避免发送任何令人反感的言论。",
            "大野猫,那种言语可能会冒犯或伤害他人,希望你能三思而行。",
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


class ChatService:
    """
    聊天服务
    
    处理普通文本聊天的 AI 交互。
    """
    
    def __init__(self):
        self.ai_client = AIClient()
    
    def get_answer(self, question: str, wxid: str, sender: str) -> None:
        """
        获取 AI 回答并发送
        
        Args:
            question: 问题内容
            wxid: 会话 ID
            sender: 发送者
        """
        # 处理被禁言用户
        rsp = process_ban(sender)
        # 私聊时不@（wxid == sender 表示私聊）
        at_user = sender if wxid != sender else ""
        
        if rsp != '':
            base_client.send_text(wxid, at_user, rsp)
            return
        
        # 调用 AI 服务
        result = self._get_answer_type(question, wxid, sender)
        
        # 根据返回类型分发处理
        if 'type' in result and result['type'] == 'gen-img':
            # 导入避免循环依赖
            from .image_service import ImageService
            ImageService().async_generate(
                f"user_input:{question}, supplementary:{result['answer']}",
                wxid,
                sender
            )
            return
        
        if 'type' in result and result['type'] == 'gen-video':
            from .video_service import VideoService
            VideoService().async_generate(
                f"user_input:{question}, supplementary:{result['answer']}",
                wxid,
                sender
            )
            return
        
        # 普通聊天回复
        rsp = result.get('answer', '')
        if 'debug' in result:
            rsp = rsp + '\n\n' + str(result['debug']).replace('$', str(result.get('ioCost', '')))
        
        base_client.send_text(wxid, at_user, rsp)
    
    def _get_answer_type(self, question: str, wxid: str, sender: str) -> dict:
        """
        获取回答及类型
        
        Returns:
            dict: 包含 type, answer, ioCost 等字段
        """
        LOG.info("开始发送给 get_answer_type")
        
        response = self.ai_client.get_llm(question, wxid, sender)
        
        if not response.success:
            return {"type": "chat", "answer": response.error_msg}
        
        result = response.data if isinstance(response.data, dict) else {"type": "chat", "answer": response.data}
        result["ioCost"] = str(response.io_cost)
        
        LOG.info("get_answer_type 回答时间为：%ss, result: %s", response.io_cost, result)
        return result
