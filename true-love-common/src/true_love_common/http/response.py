# -*- coding: utf-8 -*-
"""Unified API response model and business codes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class BizCode:
    OK = 0
    BAD_REQUEST = 100
    VALIDATION_ERROR = 100
    ROBOT_NOT_READY = 101
    SEND_FAILED = 102
    AUTH_FAILED = 103
    TOKEN_ERROR = 103
    AI_INTERNAL_ERROR = 105
    INTERNAL_ERROR = 500


@dataclass
class ApiResponse:
    code: int = BizCode.OK
    message: str = "success"
    data: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "data": self.data}

    def model_dump(self) -> dict[str, Any]:
        return self.to_dict()

    @classmethod
    def success(cls, data: Any = None, message: str = "success") -> "ApiResponse":
        return cls(code=BizCode.OK, message=message, data=data)

    @classmethod
    def error(
        cls,
        code: int | str = BizCode.BAD_REQUEST,
        message: str | None = None,
        data: Any = None,
    ) -> "ApiResponse":
        if isinstance(code, str) and message is None:
            return cls(code=1, message=code, data=data)
        return cls(code=int(code), message=message or "error", data=data)

    @classmethod
    def token_error(cls, message: str = "failed token check") -> "ApiResponse":
        return cls(code=BizCode.TOKEN_ERROR, message=message, data=None)

    @classmethod
    def internal_error(cls, message: str = "发生未知错误, 稍后再试试捏") -> "ApiResponse":
        return cls(code=BizCode.AI_INTERNAL_ERROR, message=message, data=None)


APIResponse = ApiResponse
