# -*- coding: utf-8 -*-
"""
Video Service - 视频服务

处理视频生成相关的业务逻辑。
"""

import base64
import logging
import random
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List

import requests

from . import base_client
from .ai_client import AIClient, get_video_file_path
from ..core import local_msg_id

LOG = logging.getLogger("VideoService")

# 视频生成支持的 provider
VIDEO_PROVIDERS = ["gemini"]
# VIDEO_PROVIDERS = ["gemini", "openai"]

# 线程池
_executor = ThreadPoolExecutor(max_workers=5)


class VideoService:
    """
    视频服务

    处理视频生成。
    """

    def __init__(self):
        self.ai_client = AIClient()

    def async_generate(
        self,
        question: str,
        wxid: str,
        sender: str,
        img_path_list: Optional[List[str]] = None,
    ) -> None:
        """
        异步生成视频

        Args:
            question: 提示词
            wxid: 会话 ID
            sender: 发送者
            img_path_list: 参考图片列表（可选）
        """
        msg_id = local_msg_id.get('')

        # 使用线程池执行
        _executor.submit(
            self.generate,
            question, wxid, sender, img_path_list, msg_id
        )

        # 发送等待提示
        at_user = sender if wxid != sender else ""
        base_client.send_text(wxid, at_user, "🎬视频生成中，预计需要2~10分钟，请耐心等待")

    def generate(
        self,
        question: str,
        wxid: str,
        sender: str,
        img_path_list: Optional[List[str]] = None,
        msg_id: str = ''
    ) -> None:
        """
        生成视频

        Args:
            question: 提示词
            wxid: 会话 ID
            sender: 发送者
            img_path_list: 参考图片列表（可选）
            msg_id: 消息 ID（用于文件命名）
        """
        at_user = sender if wxid != sender else ""
        provider = random.choice(VIDEO_PROVIDERS)

        LOG.info(
            "开始发送给 AI 生成视频, img_path_list=%s, provider=%s",
            img_path_list, provider
        )

        response = self.ai_client.gen_video(question, wxid, sender, img_path_list, provider)

        LOG.info("视频生成回答时间为：%s 秒", response.io_cost)

        if not response.success:
            base_client.send_text(wxid, at_user, response.error_msg)
            return

        rsp = response.data

        # 如果返回的是字符串（错误信息）
        if isinstance(rsp, str):
            base_client.send_text(wxid, at_user, rsp)
            return

        if not isinstance(rsp, dict) or 'prompt' not in rsp:
            base_client.send_text(wxid, at_user, str(rsp) if rsp else "视频生成失败")
            return

        # 发送文本结果
        res_text = f"🎬视频生成完成!\n{rsp.get('prompt')}"
        base_client.send_text(wxid, at_user, res_text)

        # 处理视频
        self._handle_video_response(rsp, wxid, at_user, msg_id)

    def _handle_video_response(
        self,
        rsp: dict,
        wxid: str,
        at_user: str,
        msg_id: str
    ) -> None:
        """
        处理视频响应

        依次判断 video_url, video_base64, video_id

        Args:
            rsp: AI 服务响应数据
            wxid: 会话 ID
            at_user: @的用户
            msg_id: 消息 ID
        """
        video_url = rsp.get('video_url')
        video_base64 = rsp.get('video_base64')
        video_id = rsp.get('video_id')
        file_path = get_video_file_path(msg_id)

        if video_url:
            # 如果是可直接访问的 URL，下载保存到本地
            try:
                video_resp = requests.get(video_url, timeout=120)
                video_resp.raise_for_status()
                with open(file_path, "wb") as f:
                    f.write(video_resp.content)
                base_client.send_video(file_path, wxid)
            except Exception as e:
                LOG.error("下载视频失败: %s", e)
                base_client.send_text(wxid, at_user, f"📹视频链接: {video_url}")

        elif video_base64:
            # 如果是 base64，保存到本地
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(video_base64))
            base_client.send_video(file_path, wxid)

        elif video_id:
            # 如果是 video_id（Gemini），从 AI 服务下载
            if self.ai_client.download_video(video_id, file_path):
                base_client.send_video(file_path, wxid)
            else:
                base_client.send_text(wxid, at_user, "呜呜~视频下载失败了，稍后再试试吧~")
