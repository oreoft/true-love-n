# -*- coding: utf-8 -*-
"""
AI Agent Skills

所有 skill 在这里统一注册，import 本模块时自动完成注册。
"""

_loaded = False


def ensure_skills_loaded():
    """确保所有 skills 已加载注册（幂等）"""
    global _loaded
    if _loaded:
        return
    _loaded = True

    # 逐个导入 skill 模块触发注册
    from . import (  # noqa: F401
        currency_skill,
        gold_skill,
        reminder_skill,
        listen_skill,
        profile_skill,
        analyze_speech_skill,
        image_skill,
        video_skill,
        search_skill,
        muninn_skill,
        deploy_skill,
        config_skill,
        wechat_qr_skill,
        job_skill,
        model_skill,
    )
