# -*- coding: utf-8 -*-
"""Common business exceptions."""

from __future__ import annotations

from typing import Any

from true_love_common.http.response import BizCode


class AppException(Exception):
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


class BusinessException(AppException):
    pass


class AuthException(BusinessException):
    def __init__(self, message: str = "failed token check", data: Any = None):
        super().__init__(code=BizCode.AUTH_FAILED, message=message, data=data)


class ValidationException(BusinessException):
    def __init__(self, message: str = "invalid parameters", data: Any = None):
        super().__init__(code=BizCode.VALIDATION_ERROR, message=message, data=data)


class InternalException(BusinessException):
    def __init__(self, message: str = "internal server error", data: Any = None):
        super().__init__(code=BizCode.INTERNAL_ERROR, message=message, data=data)
