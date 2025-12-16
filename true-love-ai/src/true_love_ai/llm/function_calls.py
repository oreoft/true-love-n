#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI Function Call 定义模块
包含各种 function call 的 schema 定义
"""

# 消息类型判断的 function call
TYPE_ANSWER_CALL = [
    {
        "type": "function",
        "function": {
            "name": "type_answer",
            "description": "type_answer",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": (
                            "the type of question, "
                            "if user wants you to generate images, please return the 'gen-img', "
                            "if it is a normal chat, please return the 'chat', "
                            "if the content requires online search You search in context first "
                            "and if there is no information, please return the 'search'"
                        )
                    },
                    "answer": {
                        "type": "string",
                        "description": (
                            "the answer of content, "
                            "if type is 'chat', please put your answer in this field, "
                            "if type is 'gen-img', "
                            "Please combine the context to give the descriptive words needed to generate the image."
                            "if type is 'search', 请在此字段中返回要搜索的内容关键词, 必须是中文, "
                            "如果其他类型, This can be empty, "
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
