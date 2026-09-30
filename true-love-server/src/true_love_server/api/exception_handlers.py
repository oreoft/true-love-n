# -*- coding: utf-8 -*-
from fastapi import FastAPI
from true_love_common.http.exceptions import AuthException, ValidationException
from true_love_common.http.response import ApiResponse
from true_love_common.integrations import fastapi as common_fastapi


def setup_exception_handlers(app: FastAPI):
    """设置异常处理器：业务异常原样返回，未处理的异常统一用下面的文案"""
    common_fastapi.setup_exception_handlers(
        app, internal_message="呜呜~服务器君好像出了点小状况，稍后再来找我玩吧~"
    )


__all__ = [
    "ApiResponse",
    "AuthException",
    "ValidationException",
    "setup_exception_handlers",
]
