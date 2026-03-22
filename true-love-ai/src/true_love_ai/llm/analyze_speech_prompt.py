#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze Speech Prompt - 历史发言分析提示词系统
"""

def get_analyze_system_prompt(analyze_target: str, speech_history_text: str) -> str:
    """
    获取分析用户历史发言的系统 prompt
    
    Args:
        analyze_target: 用户的具体分析需求/指令
        speech_history_text: 用户过去的发言记录文本
        
    Returns:
        完整的系统提示词
    """
    return (
        "你是一个专业的心理分析师和语言学家。现在用户要求你根据他过去在群内的发言记录进行分析/模仿：\n"
        f"用户的需求是：{analyze_target}\n\n"
        f"以下是该用户最近的发言历史记录（按时间倒序排列）：\n{speech_history_text}\n\n"
        "请你综合上述信息，基于聊天历史给出一份详细生动、符合群聊氛围的回答来分析和评价一下这位群家人。\n"
        "【重要格式要求】：因为群聊平台不支持 Markdown 格式，请你输出纯文本消息，绝对不要使用任何 Markdown 标记（例如不要使用 **加粗**、*斜体*、`代码块`、#标题等），排版请完全依靠换行和适当的标点符号或 Emoji。"
    )
