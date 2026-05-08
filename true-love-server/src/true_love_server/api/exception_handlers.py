# -*- coding: utf-8 -*-
from fastapi import FastAPI
from true_love_common.http.exceptions import (
    AppException,
    AuthException,
    BusinessException,
    InternalException,
    ValidationException,
)
from true_love_common.http.response import ApiResponse, BizCode
from true_love_common.integrations.fastapi import (
    app_exception_handler,
    make_generic_exception_handler,
    validation_exception_handler,
)

business_exception_handler = app_exception_handler
generic_exception_handler = make_generic_exception_handler(
    "呜呜~服务器君好像出了点小状况，稍后再来找我玩吧~"
)


def setup_exception_handlers(app: FastAPI):
    """设置异常处理器"""
    from fastapi.exceptions import RequestValidationError

    app.add_exception_handler(AppException, business_exception_handler)
    app.add_exception_handler(BusinessException, business_exception_handler)
    app.add_exception_handler(AuthException, business_exception_handler)
    app.add_exception_handler(ValidationException, business_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)


__all__ = [
    "ApiResponse",
    "BizCode",
    "AppException",
    "BusinessException",
    "AuthException",
    "ValidationException",
    "InternalException",
    "business_exception_handler",
    "generic_exception_handler",
    "setup_exception_handlers",
]
