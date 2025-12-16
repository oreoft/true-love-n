#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
外部服务模块
提供搜索、图像生成等外部服务
"""
from true_love_ai.services.search_service import fetch_baidu_references
from true_love_ai.services.image_service import ImageService

__all__ = [
    'fetch_baidu_references',
    'ImageService',
]
