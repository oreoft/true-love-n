# -*- coding: utf-8 -*-
"""Unified outbound HTTP client with trace propagation and logging."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from true_love_common.observability.sanitize import sanitize_json_text, sanitize_text
from true_love_common.observability.trace import GCP_TRACE_HEADER, get_gcp_trace_header

LOG = logging.getLogger("HttpClient")


@dataclass
class HttpResult:
    method: str
    url: str
    ok: bool
    status_code: int = 0
    headers: dict[str, str] = field(default_factory=dict)
    text: str = ""
    content: bytes = b""
    data: Any = None
    error: str = ""
    error_type: str = ""
    cost_ms: float = 0.0

    def json(self) -> Any:
        if self.data is not None:
            return self.data
        if not self.text:
            return None
        return json.loads(self.text)

    def raise_for_status(self) -> None:
        if self.ok:
            return
        raise RuntimeError(self.error or f"HTTP {self.status_code}")


def trace_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = dict(extra or {})
    headers[GCP_TRACE_HEADER] = get_gcp_trace_header()
    return headers


def request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: Any = None,
    session: Any = None,
    raise_for_status: bool = False,
    **kwargs: Any,
) -> HttpResult:
    import requests

    method = method.upper()
    merged_headers = trace_headers(headers)
    _log_start(method, url, kwargs)
    start = time.perf_counter()
    try:
        requester = session.request if session is not None else requests.request
        response = requester(method, url, headers=merged_headers, timeout=timeout, **kwargs)
        result = _result_from_response(method, url, response, (time.perf_counter() - start) * 1000)
        _log_end(result)
        if raise_for_status:
            response.raise_for_status()
        return result
    except Exception as exc:
        result = HttpResult(
            method=method,
            url=url,
            ok=False,
            error=str(exc),
            error_type=exc.__class__.__name__,
            cost_ms=(time.perf_counter() - start) * 1000,
        )
        _log_error(result)
        if raise_for_status:
            raise
        return result


def get(url: str, **kwargs: Any) -> HttpResult:
    return request("GET", url, **kwargs)


def post(url: str, **kwargs: Any) -> HttpResult:
    return request("POST", url, **kwargs)


def post_json(url: str, payload: dict[str, Any], **kwargs: Any) -> HttpResult:
    return post(url, json=payload, **kwargs)


async def async_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: Any = None,
    raise_for_status: bool = False,
    **kwargs: Any,
) -> HttpResult:
    import httpx

    method = method.upper()
    merged_headers = trace_headers(headers)
    _log_start(method, url, kwargs)
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, headers=merged_headers, **kwargs)
        result = _result_from_httpx_response(method, url, response, (time.perf_counter() - start) * 1000)
        _log_end(result)
        if raise_for_status:
            response.raise_for_status()
        return result
    except Exception as exc:
        result = HttpResult(
            method=method,
            url=url,
            ok=False,
            error=str(exc),
            error_type=exc.__class__.__name__,
            cost_ms=(time.perf_counter() - start) * 1000,
        )
        _log_error(result)
        if raise_for_status:
            raise
        return result


async def async_get(url: str, **kwargs: Any) -> HttpResult:
    return await async_request("GET", url, **kwargs)


async def async_post(url: str, **kwargs: Any) -> HttpResult:
    return await async_request("POST", url, **kwargs)


async def async_post_json(url: str, payload: dict[str, Any], **kwargs: Any) -> HttpResult:
    return await async_post(url, json=payload, **kwargs)


def _result_from_response(method: str, url: str, response: Any, cost_ms: float) -> HttpResult:
    text = response.text or ""
    return HttpResult(
        method=method,
        url=url,
        ok=200 <= response.status_code < 400,
        status_code=response.status_code,
        headers=dict(response.headers),
        text=text,
        content=response.content or b"",
        data=_safe_json(text),
        cost_ms=cost_ms,
    )


def _result_from_httpx_response(method: str, url: str, response: Any, cost_ms: float) -> HttpResult:
    text = response.text or ""
    return HttpResult(
        method=method,
        url=url,
        ok=200 <= response.status_code < 400,
        status_code=response.status_code,
        headers=dict(response.headers),
        text=text,
        content=response.content or b"",
        data=_safe_json(text),
        cost_ms=cost_ms,
    )


def _safe_json(text: str) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def _log_start(method: str, url: str, kwargs: dict[str, Any]) -> None:
    body = kwargs.get("json")
    if body is None:
        body = kwargs.get("data")
    LOG.info(
        "HTTP OUT start method=%s url=%s body=%s",
        method,
        url,
        _format_body(body),
        extra={"event": "http.out.start", "direction": "out", "method": method, "url": url},
    )


def _log_end(result: HttpResult) -> None:
    LOG.info(
        "HTTP OUT end method=%s url=%s status=%s cost_ms=%.0f body=%s",
        result.method,
        result.url,
        result.status_code,
        result.cost_ms,
        _format_body(result.data if result.data is not None else result.text, max_length=500),
        extra={
            "event": "http.out.end",
            "direction": "out",
            "method": result.method,
            "url": result.url,
            "status_code": result.status_code,
            "cost_ms": round(result.cost_ms),
        },
    )


def _log_error(result: HttpResult) -> None:
    LOG.error(
        "HTTP OUT error method=%s url=%s cost_ms=%.0f error=%s",
        result.method,
        result.url,
        result.cost_ms,
        result.error,
        extra={
            "event": "http.out.error",
            "direction": "out",
            "method": result.method,
            "url": result.url,
            "cost_ms": round(result.cost_ms),
            "error_type": result.error_type,
        },
    )


def _format_body(body: Any, max_length: int = 500) -> str:
    if body is None:
        return "empty"
    if isinstance(body, (bytes, bytearray)):
        return f"[bytes {len(body)}]"
    if isinstance(body, (dict, list)):
        return sanitize_json_text(json.dumps(body, ensure_ascii=False), max_text_length=max_length)
    return sanitize_text(str(body), max_length=max_length)
