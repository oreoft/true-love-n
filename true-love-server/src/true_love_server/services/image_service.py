# -*- coding: utf-8 -*-
"""
Image Service - 图片服务

处理图片生成和分析相关的业务逻辑。
"""

import base64
import logging
import random
from concurrent.futures import ThreadPoolExecutor

from . import base_client
from .ai_client import AIClient, get_file_path
from ..core import local_msg_id

LOG = logging.getLogger("ImageService")

# 图像生成支持的 provider
IMAGE_PROVIDERS = ["gemini"]
# IMAGE_PROVIDERS = ["openai", "gemini"]
# IMAGE_PROVIDERS = ["openai", "stability", "gemini"]

# 线程池
_executor = ThreadPoolExecutor(max_workers=10)


class ImageService:
    """
    图片服务

    处理图片生成和分析。
    """

    def __init__(self):
        self.ai_client = AIClient()

    def async_generate(
        self,
        question: str,
        wxid: str,
        sender: str,
        img_path: str = '',
    ) -> None:
        """
        异步生成图片

        Args:
            question: 提示词
            wxid: 会话 ID
            sender: 发送者
            img_path: 参考图片路径（可选）
        """
        msg_id = local_msg_id.get('')

        # 使用线程池执行
        _executor.submit(
            self.generate,
            question, wxid, sender, img_path, msg_id
        )

        # 发送等待提示
        at_user = sender if wxid != sender else ""
        base_client.send_text(wxid, at_user, "📸您的作品将在1~10分钟左右完成，请耐心等待")

    def generate(
        self,
        question: str,
        wxid: str,
        sender: str,
        img_path: str = '',
        msg_id: str = ''
    ) -> None:
        """
        生成图片

        Args:
            question: 提示词
            wxid: 会话 ID
            sender: 发送者
            img_path: 参考图片路径（可选）
            msg_id: 消息 ID（用于文件命名）
        """
        at_user = sender if wxid != sender else ""
        provider = random.choice(IMAGE_PROVIDERS)

        LOG.info(
            "开始发送给 AI 生图, img_path=%s, provider=%s",
            img_path[:10] if img_path else '', provider
        )

        response = self.ai_client.gen_image(question, wxid, sender, img_path, provider)

        LOG.info("图片生成回答时间为：%s 秒", response.io_cost)

        if not response.success:
            base_client.send_text(wxid, at_user, response.error_msg)
            return

        rsp = response.data
        if not isinstance(rsp, dict) or 'prompt' not in rsp:
            base_client.send_text(wxid, at_user, str(rsp) if rsp else "图片生成失败")
            return

        # 获取 provider 首字母
        provider_initial = provider[0].upper() if provider else 'U'

        # 发送文本结果
        res_text = f"🎨绘画完成!\n{rsp.get('prompt')}\n\n该图片由{provider_initial}家提供"
        base_client.send_text(wxid, at_user, res_text)

        # 保存并发送图片
        file_path = get_file_path(msg_id)
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(rsp.get('img')))
        base_client.send_img(file_path, wxid)

    def async_analyze(
        self,
        question: str,
        wxid: str,
        sender: str,
        img_path: str
    ) -> None:
        """
        异步分析图片

        Args:
            question: 问题
            wxid: 会话 ID
            sender: 发送者
            img_path: 图片路径
        """
        # 使用线程池执行
        _executor.submit(
            self.analyze,
            question, wxid, sender, img_path
        )

        # 发送等待提示
        at_user = sender if wxid != sender else ""
        base_client.send_text(wxid, at_user, "🔍让我仔细瞧瞧，请耐心等待")

    def analyze(
        self,
        question: str,
        wxid: str,
        sender: str,
        img_path: str
    ) -> None:
        """
        分析图片

        Args:
            question: 问题
            wxid: 会话 ID
            sender: 发送者
            img_path: 图片路径
        """
        at_user = sender if wxid != sender else ""

        LOG.info("开始发送给 AI 分析, img_path=%s", img_path[:10] if img_path else '')

        response = self.ai_client.analyze_image(question, wxid, sender, img_path)

        LOG.info("图片分析回答时间为：%s 秒", response.io_cost)

        if not response.success:
            base_client.send_text(wxid, at_user, response.error_msg)
            return

        base_client.send_text(wxid, at_user, response.data)

    def get_img_type(self, question: str) -> dict:
        """
        判断图片处理类型

        Args:
            question: 问题内容

        Returns:
            dict: 包含 type 的字典
        """
        LOG.info("开始发送给 get_img_type")

        response = self.ai_client.get_img_type(question)

        LOG.info("get_img_type 回答时间为：%ss, result: %s", response.io_cost, response.data)

        if not response.success:
            return {"error": response.error_msg}

        return response.data if isinstance(response.data, dict) else {"prompt": response.data}

    def handle_image_request(
        self,
        question: str,
        img_path: str,
        wxid: str,
        sender: str
    ) -> None:
        """
        处理图片请求（判断分析还是生成）

        Args:
            question: 问题内容
            img_path: 图片路径
            wxid: 会话 ID
            sender: 发送者
        """
        result = self.get_img_type(question)

        if 'type' in result and result['type'] == 'analyze_img':
            self.async_analyze(question, wxid, sender, img_path)
        else:
            # 其他都是改图/生图
            prompt = result.get('prompt', question) if isinstance(result, dict) else question
            self.async_generate(prompt, wxid, sender, img_path)
