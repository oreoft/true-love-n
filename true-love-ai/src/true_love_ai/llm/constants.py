#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
常量配置模块
包含模型名称、API URL 等配置
"""

# ==================== 模型配置 ====================
OPENAI_MODEL = "gpt-5.2"
OPENAI_VISION_MODEL = "gpt-5.2"
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"
DEEPSEEK_MODEL = "deepseek/deepseek-reasoner"

# 默认使用的模型
DEFAULT_MODEL = OPENAI_MODEL

# ==================== 对话配置 ====================
MAX_CONVERSATION_LENGTH = 10  # 最大对话历史长度
