#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像服务模块
提供 Stability AI 图像生成、编辑等功能
"""
import base64
import logging
from io import BytesIO

import requests

from true_love_ai.configuration import Config

LOG = logging.getLogger("ImageService")

# ==================== Stability AI 配置 ====================
SD_BASE_URL = "https://api.stability.ai/v2beta/stable-image"
SD_GENERATE_URL = f"{SD_BASE_URL}/generate/ultra"
SD_CONTROL_URL = f"{SD_BASE_URL}/control/structure"
SD_ERASE_URL = f"{SD_BASE_URL}/edit/erase"
SD_REPLACE_URL = f"{SD_BASE_URL}/edit/search-and-replace"
SD_REMOVE_BG_URL = f"{SD_BASE_URL}/edit/remove-background"

# 图像操作类型到 URL 的映射
SD_URL_MAP = {
    'gen_by_img': SD_CONTROL_URL,
    'erase_img': SD_ERASE_URL,
    'replace_img': SD_REPLACE_URL,
    'remove_background_img': SD_REMOVE_BG_URL
}


class ImageService:
    """Stability AI 图像服务"""
    
    def __init__(self):
        self.api_key = Config().PLATFORM_KEY.get('sd', '')
    
    def _get_headers(self) -> dict:
        """获取请求头"""
        return {
            "authorization": f"Bearer {self.api_key}",
            "accept": "application/json; type=image/"
        }
    
    def generate_image(self, prompt: str) -> dict:
        """
        根据文字描述生成图像
        
        Args:
            prompt: 图像描述词
            
        Returns:
            {"prompt": str, "img": base64_str}
        """
        try:
            LOG.info(f"开始生成图像, prompt: {prompt[:50]}...")
            
            response = requests.post(
                SD_GENERATE_URL,
                headers=self._get_headers(),
                files={"none": ''},
                data={
                    "prompt": prompt,
                    "output_format": "jpeg",
                    "aspect_ratio": "1:1"
                },
            )
            
            if response.status_code == 200:
                return {"prompt": prompt, "img": response.json()['image']}
            else:
                LOG.error(f"图像生成失败, status: {response.status_code}, result: {response.json()}")
                raise ValueError("生成失败! 内容太不堪入目啦~")
                
        except requests.Timeout:
            LOG.error("图像生成超时")
            raise
        except Exception:
            LOG.exception("图像生成错误")
            raise
    
    def edit_image(self, img_data: str, operation_type: str, prompt: str) -> dict:
        """
        编辑/处理图像
        
        Args:
            img_data: base64 编码的图像数据
            operation_type: 操作类型 (gen_by_img, erase_img, replace_img, remove_background_img)
            prompt: 操作描述词
            
        Returns:
            {"prompt": str, "img": base64_str}
        """
        try:
            url = SD_URL_MAP.get(operation_type, SD_GENERATE_URL)
            LOG.info(f"开始编辑图像, type: {operation_type}, prompt: {prompt[:50]}...")
            
            response = requests.post(
                url,
                headers=self._get_headers(),
                files={
                    "image": BytesIO(base64.b64decode(img_data))
                },
                data={
                    "prompt": prompt,
                    "search_prompt": prompt,
                    "control_strength": 0.7,
                    "output_format": "png"
                },
            )
            
            if response.status_code == 200:
                return {"prompt": prompt, "img": response.json()['image']}
            else:
                LOG.error(f"图像编辑失败, status: {response.status_code}, result: {response.json()}")
                raise ValueError("生成失败! 内容太不堪入目啦~")
                
        except requests.Timeout:
            LOG.error("图像编辑超时")
            raise
        except Exception:
            LOG.exception("图像编辑错误")
            raise
