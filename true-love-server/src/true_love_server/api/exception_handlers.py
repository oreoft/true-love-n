# -*- coding: utf-8 -*-
"""
Exception Handlers - 全局异常处理

统一的异常处理和响应格式。
"""

import logging
import traceback
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

LOG = logging.getLogger("ExceptionHandler")


class ApiResponse(BaseModel):
    """统一响应格式"""
    code: int = 0
    message: str = "success"
    data: Any = None


class BusinessException(Exception):
    """业务异常"""

    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


class AuthException(BusinessException):
    """认证异常"""

    def __init__(self, message: str = "呜呜~身份验证失败了捏，检查一下 token 吧~"):
        super().__init__(code=103, message=message)


class ValidationException(BusinessException):
    """验证异常"""

    def __init__(self, message: str = "诶嘿~参数好像有点问题呢，再检查一下吧~"):
        super().__init__(code=100, message=message)


async def business_exception_handler(request: Request, exc: BusinessException):
    """处理业务异常"""
    LOG.warning(
        "业务异常: [%s] %s, path: %s",
        exc.code,
        exc.message,
        request.url.path
    )
    return JSONResponse(
        status_code=200,
        content=ApiResponse(
            code=exc.code,
            message=exc.message,
            data=exc.data
        ).model_dump()
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """处理未捕获的异常"""
    LOG.error(
        "未捕获异常: %s, path: %s\n%s",
        str(exc),
        request.url.path,
        traceback.format_exc()
    )
    return JSONResponse(
        status_code=200,
        content=ApiResponse(
            code=500,
            message="呜呜~服务器君好像出了点小状况，稍后再来找我玩吧~",
            data=None
        ).model_dump()
    )


def setup_exception_handlers(app: FastAPI):
    """设置异常处理器"""
    app.add_exception_handler(BusinessException, business_exception_handler)
    app.add_exception_handler(AuthException, business_exception_handler)
    app.add_exception_handler(ValidationException, business_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
