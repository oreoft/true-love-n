#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI Function Call 定义模块
包含各种 function call 的 schema 定义
"""

# Intent recognition function call
TYPE_ANSWER_CALL = [
    {
        "type": "function",
        "function": {
            "name": "type_answer",
            "description": "Analyze user intent and generate response",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["chat", "search", "gen-img", "gen-video"],
                        "description": (
                            "Intent type: "
                            "'chat' for general conversation or questions you can answer from knowledge, "
                            "'search' for real-time information that requires web search, "
                            "'gen-img' for image generation requests, "
                            "'gen-video' for video generation requests"
                        )
                    },
                    "answer": {
                        "type": "string",
                        "description": (
                            "For 'chat': your response to the user. "
                            "For 'gen-img': English prompt for image generation. "
                            "For 'gen-video': English prompt for video generation. "
                            "For 'search': Chinese search keywords that are complete, specific, "
                            "and self-contained based on conversation context."
                        )
                    },
                },
                "required": ["type", "answer"]
            }
        }
    }
]

# 图像操作类型判断的 function call
IMG_TYPE_ANSWER_CALL = [
    {
        "type": "function",
        "function": {
            "name": "img_type_answer_call",
            "description": "img_type_answer_call",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": (
                            "Based on the user description, determine which of the following types it belongs to: "
                            "generate image (gen_by_img), "
                            "erase object from image (erase_img), "
                            "replace object in image (replace_img), "
                            "analyzing or interpreting image (analyze_img), "
                            "remove image background (remove_background_img). "
                            "Please provide the type."
                        )
                    },
                    "answer": {
                        "type": "string",
                        "description": "Here is your translation and colorization answer, please put your answer in this field"
                    },
                },
                "required": ["type", "answer"]
            }
        }
    }
]

