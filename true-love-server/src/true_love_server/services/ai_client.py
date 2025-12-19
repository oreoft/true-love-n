# -*- coding: utf-8 -*-
"""
AI Client - AI 服务 HTTP 客户端

负责与 AI 服务的所有 HTTP 通信。
"""

import base64
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

import requests

from ..core import Config

LOG = logging.getLogger("AIClient")


@dataclass
class AIResponse:
    """AI 服务响应"""
    success: bool
    data: Optional[Any] = None
    error_msg: Optional[str] = None
    io_cost: float = 0.0


def is_friendly_message(msg: str) -> bool:
    """判断是否是 AI 服务处理过的友好文案（二次元风格）"""
    if not msg or not isinstance(msg, str):
        return False
    friendly_keywords = ['~', '呜呜', '啦', '捏', '吧~', '呢~', '哦~', '呀~']
    return any(kw in msg for kw in friendly_keywords)


def image_to_base64(image_path: str) -> str:
    """将图片文件转换为 Base64 编码字符串"""
    if image_path:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())
            return encoded_string.decode('utf-8')
    return ""


class AIClient:
    """
    AI 服务 HTTP 客户端
    
    统一封装与 AI 服务的 HTTP 通信。
    """
    
    def __init__(self):
        config = Config()
        self.token = config.HTTP_TOKEN
        self.ai_host = config.AI_SERVICE.get("host", "https://notice.someget.work")
    
    def _request(
        self,
        endpoint: str,
        data: dict,
        timeout: int = 120,
        friendly_error: str = "呜呜~服务好像出问题了捏，稍后再试试吧~"
    ) -> AIResponse:
        """
        统一的 HTTP 请求方法
        
        Args:
            endpoint: API 端点
            data: 请求数据
            timeout: 超时时间（秒）
            friendly_error: 友好错误提示
            
        Returns:
            AIResponse: 响应结果
        """
        url = f'{self.ai_host}{endpoint}'
        headers = {'Content-Type': 'application/json'}
        data['token'] = self.token
        
        start_time = time.time()
        
        try:
            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(data),
                timeout=timeout
            )
            
            io_cost = round(time.time() - start_time, 2)
            
            # 检查 HTTP 状态
            if response.status_code != 200:
                LOG.error(
                    "%s请求失败, status_code: %s, body: %s",
                    endpoint, response.status_code, response.text[:500]
                )
                return AIResponse(
                    success=False,
                    error_msg=friendly_error,
                    io_cost=io_cost
                )
            
            # 解析 JSON
            json_data = response.json()
            
            # 检查业务码
            code = json_data.get('code', 0)
            if code != 0:
                error_msg = json_data.get('message', '未知错误')
                LOG.error("%s返回错误, code: %s, message: %s", endpoint, code, error_msg)
                # 如果是 AI 服务处理过的友好文案，直接返回
                if is_friendly_message(error_msg):
                    return AIResponse(success=False, error_msg=error_msg, io_cost=io_cost)
                return AIResponse(success=False, error_msg=friendly_error, io_cost=io_cost)
            
            rsp_data = json_data.get('data')
            if rsp_data == '':
                return AIResponse(success=False, error_msg="返回数据为空", io_cost=io_cost)
            
            return AIResponse(success=True, data=rsp_data, io_cost=io_cost)
            
        except requests.exceptions.Timeout:
            LOG.error("发送到%s超时", endpoint)
            return AIResponse(
                success=False,
                error_msg="AI酱思考太久啦~等不及了，稍后再试试吧~",
                io_cost=round(time.time() - start_time, 2)
            )
        except json.JSONDecodeError as e:
            LOG.error("%s响应JSON解析失败: %s", endpoint, e)
            return AIResponse(
                success=False,
                error_msg="呀~服务器君说的话我听不懂，稍后再试试吧~",
                io_cost=round(time.time() - start_time, 2)
            )
        except Exception as e:
            LOG.error("发送到%s出错: %s", endpoint, e)
            return AIResponse(
                success=False,
                error_msg="呜呜~出了点小状况，稍后再试试捏~",
                io_cost=round(time.time() - start_time, 2)
            )
    
    def get_llm(self, question: str, wxid: str, sender: str) -> AIResponse:
        """
        获取 LLM 回答
        
        Args:
            question: 问题内容
            wxid: 微信 ID（会话 ID）
            sender: 发送者
            
        Returns:
            AIResponse: 包含 type 和 answer 的响应
        """
        data = {
            "content": question,
            "wxid": wxid,
            "sender": sender,
        }
        return self._request(
            "/get-llm",
            data,
            timeout=120,
            friendly_error="呜呜~AI服务好像出问题了捏，稍后再试试吧~"
        )
    
    def get_img_type(self, question: str) -> AIResponse:
        """
        判断图片处理类型（分析还是生成）
        
        Args:
            question: 问题内容
            
        Returns:
            AIResponse: 包含 type 的响应
        """
        data = {"content": question}
        return self._request(
            "/get-img-type",
            data,
            timeout=60,
            friendly_error="呜呜~识别服务好像出问题了捏，稍后再试试吧~"
        )
    
    def gen_image(
        self,
        question: str,
        wxid: str,
        sender: str,
        img_path: str = "",
        provider: str = ""
    ) -> AIResponse:
        """
        生成图片
        
        Args:
            question: 提示词
            wxid: 微信 ID
            sender: 发送者
            img_path: 参考图片路径（可选）
            provider: 模型提供商
            
        Returns:
            AIResponse: 包含 prompt 和 img (base64) 的响应
        """
        data = {
            "content": question,
            "wxid": wxid,
            "sender": sender,
            "img_data": image_to_base64(img_path),
            "provider": provider,
        }
        return self._request(
            "/gen-img",
            data,
            timeout=300,
            friendly_error="呜呜~画画服务好像出问题了捏，稍后再试试吧~"
        )
    
    def analyze_image(
        self,
        question: str,
        wxid: str,
        sender: str,
        img_path: str
    ) -> AIResponse:
        """
        分析图片
        
        Args:
            question: 问题
            wxid: 微信 ID
            sender: 发送者
            img_path: 图片路径
            
        Returns:
            AIResponse: 分析结果
        """
        data = {
            "content": question,
            "wxid": wxid,
            "sender": sender,
            "img_data": image_to_base64(img_path),
        }
        return self._request(
            "/get-analyze",
            data,
            timeout=120,
            friendly_error="呜呜~分析服务好像出问题了捏，稍后再试试吧~"
        )
    
    def gen_video(
        self,
        question: str,
        wxid: str,
        sender: str,
        img_path_list: list = None,
        provider: str = ""
    ) -> AIResponse:
        """
        生成视频
        
        Args:
            question: 提示词
            wxid: 微信 ID
            sender: 发送者
            img_path_list: 参考图片列表（可选）
            provider: 模型提供商
            
        Returns:
            AIResponse: 包含 prompt 和视频数据的响应
        """
        data = {
            "content": question,
            "wxid": wxid,
            "sender": sender,
            "provider": provider,
        }
        
        if img_path_list:
            data["img_data_list"] = [image_to_base64(p) for p in img_path_list if p]
        
        return self._request(
            "/gen-video",
            data,
            timeout=600,
            friendly_error="呜呜~视频生成服务好像出问题了捏，稍后再试试吧~"
        )
    
    def download_video(self, video_id: str, save_path: str) -> bool:
        """
        下载视频
        
        Args:
            video_id: 视频 ID
            save_path: 保存路径
            
        Returns:
            bool: 是否成功
        """
        try:
            download_url = f'{self.ai_host}/download-video/{video_id}?token={self.token}'
            LOG.info("从AI服务下载视频, video_id=%s", video_id)
            
            response = requests.get(download_url, timeout=300, stream=True)
            response.raise_for_status()
            
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            LOG.info("视频下载完成: %s", save_path)
            return True
        except Exception as e:
            LOG.error("从AI服务下载视频失败: %s", e)
            return False


# 文件路径工具函数
def get_file_path(msg_id: str, file_type: str = 'png') -> str:
    """获取生成图片的保存路径"""
    download_directory = 'gen-img/'
    if not os.path.exists(download_directory):
        os.makedirs(download_directory)
    local_filename = f'{msg_id if msg_id else str(time.time())}.{file_type}'
    return os.path.join(download_directory, local_filename)


def get_video_file_path(msg_id: str) -> str:
    """获取生成视频的保存路径"""
    download_directory = 'gen-video/'
    if not os.path.exists(download_directory):
        os.makedirs(download_directory)
    local_filename = f'{msg_id if msg_id else str(time.time())}.mp4'
    return os.path.join(download_directory, local_filename)
