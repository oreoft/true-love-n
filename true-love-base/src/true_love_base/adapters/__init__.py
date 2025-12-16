# -*- coding: utf-8 -*-
"""
Adapters package - SDK适配器

提供不同微信SDK的适配器实现。
当前支持: wxautox4
"""

from true_love_base.adapters.wxauto_adapter import WxAutoClient

__all__ = [
    "WxAutoClient",
]
