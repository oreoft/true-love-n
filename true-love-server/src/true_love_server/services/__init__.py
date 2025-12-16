# -*- coding: utf-8 -*-
"""
Services module - 服务模块

包含 AI 服务、基础通信、语音识别等服务。
"""

from . import base_client
from . import chatgpt
from .asr_utils import do_asr

__all__ = ["base_client", "chatgpt", "do_asr"]
