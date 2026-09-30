# -*- coding: utf-8 -*-
"""FastAPI/Starlette observability middleware."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from true_love_common.http.exceptions import AppException
from true_love_common.http.response import ApiResponse, BizCode
from true_love_common.observability.sanitize import (
    DEFAULT_MAX_TEXT_LENGTH,
    sanitize_json_text,
    sanitize_text,
)
from true_love_common.observability.trace import (
    GCP_TRACE_HEADER,
    get_gcp_trace_header,
    set_trace_from_gcp_header,
)

LOG = logging.getLogger("HttpMiddleware")
EXCEPTION_LOG = logging.getLogger("ExceptionHandler")


SKIP_METHODS = frozenset({"OPTIONS"})
BINARY_CONTENT_TYPES = (
    "audio/",
    "image/",
    "video/",
    "application/octet-stream",
    "application/pdf",
)


class HttpLoggingMiddleware(BaseHTTPMiddleware):
    """Unified inbound HTTP logging and GCP trace middleware."""

    def __init__(
        self,
        app,
        *,
        service_name: str,
        skip_paths: set[str] | None = None,
        max_response_body_chars: int = 500,
    ) -> None:
        super().__init__(app)
        self.service_name = service_name
        self.skip_paths = skip_paths if skip_paths is not None else {"/health", "/ping"}
        self.max_response_body_chars = max_response_body_chars

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = uuid.uuid4().hex[:8]
        request.state.request_id = request_id

        trace_context = set_trace_from_gcp_header(request.headers.get(GCP_TRACE_HEADER))
        path = request.url.path
        skip_log = (
            any(path == p or path.startswith(p + "/") for p in self.skip_paths)
            or request.method in SKIP_METHODS
        )

        body = b""
        if request.method in {"POST", "PUT", "PATCH"}:
            body = await request.body()
            request._receive = _make_receive(body)

        if not skip_log:
            LOG.info(
                "HTTP IN start service=%s request_id=%s method=%s path=%s query=%s client=%s body=%s",
                self.service_name,
                request_id,
                request.method,
                request.url.path,
                request.url.query or "-",
                request.client.host if request.client else "-",
                _format_body(
                    body,
                    content_type=request.headers.get("content-type", ""),
                    max_chars=DEFAULT_MAX_TEXT_LENGTH,
                )
                if body
                else "empty",
                extra={
                    "event": "http.in.start",
                    "direction": "in",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "extra_fields": {"query": request.url.query or "-", "trace_id": trace_context.trace_id},
                },
            )

        start_time = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            cost_ms = (time.perf_counter() - start_time) * 1000
            LOG.exception(
                "HTTP IN error service=%s request_id=%s method=%s path=%s cost_ms=%.0f error=%s",
                self.service_name,
                request_id,
                request.method,
                request.url.path,
                cost_ms,
                exc,
                extra={
                    "event": "http.in.error",
                    "direction": "in",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "cost_ms": round(cost_ms),
                    "error_type": exc.__class__.__name__,
                },
            )
            raise

        cost_ms = (time.perf_counter() - start_time) * 1000
        content_type = response.media_type or response.headers.get("content-type", "")
        is_streaming_or_binary = "text/event-stream" in content_type or content_type.startswith(BINARY_CONTENT_TYPES)

        if is_streaming_or_binary:
            response.headers[GCP_TRACE_HEADER] = get_gcp_trace_header()
            response.headers["X-Process-Time"] = f"{cost_ms:.0f}ms"
            if not skip_log:
                LOG.info(
                    "HTTP IN end service=%s request_id=%s method=%s path=%s status=%s cost_ms=%.0f body=%s",
                    self.service_name,
                    request_id,
                    request.method,
                    request.url.path,
                    response.status_code,
                    cost_ms,
                    f"[stream/binary {content_type or 'unknown'}]",
                    extra={
                        "event": "http.in.end",
                        "direction": "in",
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "cost_ms": round(cost_ms),
                    },
                )
            return response

        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk

        if not skip_log:
            LOG.info(
                "HTTP IN end service=%s request_id=%s method=%s path=%s status=%s cost_ms=%.0f body=%s",
                self.service_name,
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                cost_ms,
                _format_body(
                    response_body,
                    content_type=content_type,
                    max_chars=self.max_response_body_chars,
                ),
                extra={
                    "event": "http.in.end",
                    "direction": "in",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "cost_ms": round(cost_ms),
                },
            )

        headers = dict(response.headers)
        headers[GCP_TRACE_HEADER] = get_gcp_trace_header()
        headers["X-Process-Time"] = f"{cost_ms:.0f}ms"
        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )


def _make_receive(body: bytes):
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


def _format_body(
    body: bytes,
    *,
    content_type: str,
    max_chars: int,
) -> str:
    if not body:
        return "empty"

    if content_type.startswith(BINARY_CONTENT_TYPES):
        return f"[binary {content_type or 'unknown'}, {len(body)} bytes]"

    text = body.decode("utf-8", errors="replace")
    if "json" in content_type:
        return sanitize_json_text(text, max_text_length=max_chars)
    return sanitize_text(text, max_length=max_chars)


async def app_exception_handler(request: Request, exc: AppException):
    EXCEPTION_LOG.warning(
        "Business exception code=%s message=%s path=%s",
        exc.code,
        exc.message,
        request.url.path,
    )
    return JSONResponse(
        status_code=200,
        content=ApiResponse(code=exc.code, message=exc.message, data=exc.data).to_dict(),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    EXCEPTION_LOG.warning("Request validation failed path=%s errors=%s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=200,
        content=ApiResponse(code=BizCode.VALIDATION_ERROR, message="invalid parameters", data=exc.errors()).to_dict(),
    )


def make_generic_exception_handler(internal_message: str = "internal server error"):
    async def generic_exception_handler(request: Request, exc: Exception):
        EXCEPTION_LOG.exception("Unhandled exception path=%s error=%s", request.url.path, exc)
        return JSONResponse(
            status_code=200,
            content=ApiResponse(code=BizCode.INTERNAL_ERROR, message=internal_message, data=None).to_dict(),
        )

    return generic_exception_handler


def setup_exception_handlers(app: FastAPI, *, internal_message: str = "internal server error") -> None:
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, make_generic_exception_handler(internal_message))
