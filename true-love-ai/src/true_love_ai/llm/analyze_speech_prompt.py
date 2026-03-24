#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze Speech Prompt - 历史发言分析提示词系统
"""


def get_analyze_system_prompt(speech_history_text: str, metadata: dict = None) -> str:
    """
    获取分析用户历史发言的系统 prompt

    Args:
        speech_history_text: 用户过去的发言记录文本
        metadata: 参数字典，包含 target, target_name, is_self 等

    Returns:
        完整的系统提示词
    """
    metadata = metadata or {}
    is_self = metadata.get("is_self", False)
    target_name = metadata.get("target_name", "")
    analyze_target = metadata.get("target", "分析聊天记录并总结其人物性格特点")

    # 根据是否是"分析自己"来决定称呼
    # 如果分析自己 -> 你
    # 如果分析他人 -> 群昵称
    if is_self:
        name_ref = f"你(昵称是{target_name})"
        pronoun_instruct = "分析的主角是给你发消息的那个人，你要对他用'你'来称呼进行对话式分析。"
    else:
        name_ref = f"该群家人(昵称是{target_name})"
        pronoun_instruct = f"分析的主角是群里的{name_ref}，你要以第三人称（或直接叫名字）来客观评价他，**绝对不要**称呼其为'你'。"

    return (
        f"你是一个专业的心理分析师和语言学家，负责根据聊天记录分析群家人的性格以及人物特点，语言幽默生动，符合群聊氛围\n"
        f"分析需求：{analyze_target}\n"
        f"人称要求：{pronoun_instruct}\n\n"
        f"以下是{name_ref}最近的群内发言历史记录（按时间倒序排列）：\n{speech_history_text}\n\n"
        f"请你综合上述信息，基于这些聊天历史给出一份详细生动、符合群聊氛围的分析报告。报告的主角是：{name_ref}。\n"
        f"【注意】报告中请使用{name_ref}作为称呼核心。如果是分析别人，请用第三人称；如果是分析自己，请用第二人称'你'。\n"
        "【重要格式要求】：请你输出纯文本消息，绝对不要使用任何 Markdown 标记（如 **加粗** 等），靠换行排版。\n"
        "另外开头不要有任何客套话,类似'好的，收到分析请求。'之类的，因为等待的时候就已经告知了"
    )
