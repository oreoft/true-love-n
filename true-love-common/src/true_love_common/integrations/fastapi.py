# -*- coding: utf-8 -*-
"""FastAPI/Starlette observability middleware."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from true_love_common.observability.sanitize import (
    DEFAULT_MAX_TEXT_LENGTH,
    DEFAULT_SENSITIVE_KEYS,
    sanitize_json_text,
    sanitize_text,
)
from true_love_common.observability.trace import (
    GCP_TRACE_HEADER,
    get_gcp_trace_header,
    set_trace_from_gcp_header,
)

LOG = logging.getLogger("HttpMiddleware")


@dataclass(frozen=True)
class HttpLoggingConfig:
    service_name: str
    skip_paths: set[str] = field(default_factory=lambda: {"/health", "/ping"})
    skip_methods: set[str] = field(default_factory=lambda: {"OPTIONS"})
    log_request_body: bool = True
    log_response_body: bool = True
    max_request_body_chars: int = DEFAULT_MAX_TEXT_LENGTH
    max_response_body_chars: int = 500
    sensitive_keys: set[str] | frozenset[str] = DEFAULT_SENSITIVE_KEYS
    binary_content_types: tuple[str, ...] = (
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
        skip_methods: set[str] | None = None,
        log_request_body: bool = True,
        log_response_body: bool = True,
        max_request_body_chars: int = DEFAULT_MAX_TEXT_LENGTH,
        max_response_body_chars: int = 500,
        sensitive_keys: set[str] | frozenset[str] = DEFAULT_SENSITIVE_KEYS,
        binary_content_types: tuple[str, ...] | None = None,
    ) -> None:
        super().__init__(app)
        self.config = HttpLoggingConfig(
            service_name=service_name,
            skip_paths=skip_paths if skip_paths is not None else {"/health", "/ping"},
            skip_methods=skip_methods if skip_methods is not None else {"OPTIONS"},
            log_request_body=log_request_body,
            log_response_body=log_response_body,
            max_request_body_chars=max_request_body_chars,
            max_response_body_chars=max_response_body_chars,
            sensitive_keys=sensitive_keys,
            binary_content_types=binary_content_types
            if binary_content_types is not None
            else HttpLoggingConfig(service_name=service_name).binary_content_types,
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = uuid.uuid4().hex[:8]
        request.state.request_id = request_id

        trace_context = set_trace_from_gcp_header(request.headers.get(GCP_TRACE_HEADER))
        skip_log = request.url.path in self.config.skip_paths or request.method in self.config.skip_methods

        body = b""
        if self.config.log_request_body and request.method in {"POST", "PUT", "PATCH"}:
            body = await request.body()
            request._receive = _make_receive(body)

        if not skip_log:
            LOG.info(
                "HTTP IN start service=%s request_id=%s method=%s path=%s query=%s client=%s body=%s",
                self.config.service_name,
                request_id,
                request.method,
                request.url.path,
                request.url.query or "-",
                request.client.host if request.client else "-",
                _format_body(
                    body,
                    content_type=request.headers.get("content-type", ""),
                    max_chars=self.config.max_request_body_chars,
                    sensitive_keys=self.config.sensitive_keys,
                    binary_content_types=self.config.binary_content_types,
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
                self.config.service_name,
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
        is_streaming_or_binary = "text/event-stream" in content_type or content_type.startswith(
            self.config.binary_content_types
        )

        if is_streaming_or_binary:
            response.headers[GCP_TRACE_HEADER] = get_gcp_trace_header()
            response.headers["X-Process-Time"] = f"{cost_ms:.0f}ms"
            if not skip_log:
                LOG.info(
                    "HTTP IN end service=%s request_id=%s method=%s path=%s status=%s cost_ms=%.0f body=%s",
                    self.config.service_name,
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
                self.config.service_name,
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                cost_ms,
                _format_body(
                    response_body,
                    content_type=content_type,
                    max_chars=self.config.max_response_body_chars,
                    sensitive_keys=self.config.sensitive_keys,
                    binary_content_types=self.config.binary_content_types,
                )
                if self.config.log_response_body
                else "[disabled]",
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
    sensitive_keys: set[str] | frozenset[str],
    binary_content_types: tuple[str, ...],
) -> str:
    if not body:
        return "empty"

    if content_type.startswith(binary_content_types):
        return f"[binary {content_type or 'unknown'}, {len(body)} bytes]"

    text = body.decode("utf-8", errors="replace")
    if "json" in content_type:
        return sanitize_json_text(
            text,
            sensitive_keys=sensitive_keys,
            max_text_length=max_chars,
        )
    return sanitize_text(text, max_length=max_chars)
