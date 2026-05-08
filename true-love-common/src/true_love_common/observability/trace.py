# -*- coding: utf-8 -*-
"""GCP trace context helpers.

Only the GCP trace header is supported:
    X-Cloud-Trace-Context: TRACE_ID/SPAN_ID;o=1
"""

from __future__ import annotations

import contextvars
import random
import re
import uuid
from dataclasses import dataclass

GCP_TRACE_HEADER = "X-Cloud-Trace-Context"
_TRACE_ID_RE = re.compile(r"^[0-9a-fA-F]{32}$")
_SPAN_ID_RE = re.compile(r"^\d{1,20}$")

_trace_id: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")
_span_id: contextvars.ContextVar[str] = contextvars.ContextVar("span_id", default="-")
_trace_sampled: contextvars.ContextVar[bool] = contextvars.ContextVar("trace_sampled", default=False)


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    span_id: str = "-"
    sampled: bool = False


def new_trace_id() -> str:
    """Return a GCP-compatible 32 hex character trace id."""
    return uuid.uuid4().hex


def new_span_id() -> str:
    """Return a GCP-compatible decimal span id."""
    return str(random.getrandbits(63) or 1)


def get_trace_id() -> str:
    return _trace_id.get()


def get_span_id() -> str:
    return _span_id.get()


def is_trace_sampled() -> bool:
    return _trace_sampled.get()


def get_trace_context() -> TraceContext:
    return TraceContext(
        trace_id=get_trace_id(),
        span_id=get_span_id(),
        sampled=is_trace_sampled(),
    )


def set_trace_id(trace_id: str, span_id: str | None = None, sampled: bool | None = None) -> TraceContext:
    """Set the current trace id and optionally span/sample state."""
    context = TraceContext(
        trace_id=_normalize_trace_id(trace_id) or new_trace_id(),
        span_id=_normalize_span_id(span_id) if span_id is not None else get_span_id(),
        sampled=is_trace_sampled() if sampled is None else bool(sampled),
    )
    set_trace_context(context)
    return context


def set_trace_context(context: TraceContext) -> TraceContext:
    trace_id = _normalize_trace_id(context.trace_id) or new_trace_id()
    span_id = _normalize_span_id(context.span_id) or "-"
    _trace_id.set(trace_id)
    _span_id.set(span_id)
    _trace_sampled.set(bool(context.sampled))
    return TraceContext(trace_id=trace_id, span_id=span_id, sampled=bool(context.sampled))


def clear_trace_context() -> None:
    _trace_id.set("-")
    _span_id.set("-")
    _trace_sampled.set(False)


def set_trace_from_gcp_header(header_value: str | None, *, create_if_missing: bool = True) -> TraceContext:
    """Parse and set trace context from X-Cloud-Trace-Context.

    Invalid or empty headers create a fresh trace id by default.
    """
    context = parse_gcp_trace_header(header_value)
    if context is None:
        context = TraceContext(new_trace_id(), new_span_id(), False) if create_if_missing else TraceContext("-", "-", False)
    return set_trace_context(context)


def get_gcp_trace_header(*, span_id: str | None = None) -> str:
    """Return the current context formatted as X-Cloud-Trace-Context."""
    trace_id = _normalize_trace_id(get_trace_id()) or new_trace_id()
    current_span_id = _normalize_span_id(span_id) if span_id is not None else _normalize_span_id(get_span_id())
    if not current_span_id or current_span_id == "-":
        current_span_id = new_span_id()
    sampled = "1" if is_trace_sampled() else "0"
    return f"{trace_id}/{current_span_id};o={sampled}"


def parse_gcp_trace_header(header_value: str | None) -> TraceContext | None:
    if not header_value:
        return None

    value = header_value.strip()
    if not value:
        return None

    trace_part, _, options_part = value.partition(";")
    trace_id, sep, span_id = trace_part.partition("/")
    trace_id = _normalize_trace_id(trace_id)
    if not trace_id:
        return None

    normalized_span_id = _normalize_span_id(span_id) if sep else "-"
    sampled = _parse_sampled(options_part)
    return TraceContext(trace_id=trace_id, span_id=normalized_span_id or "-", sampled=sampled)


def _normalize_trace_id(value: str | None) -> str:
    if not value:
        return ""
    value = value.strip().lower()
    return value if _TRACE_ID_RE.match(value) else ""


def _normalize_span_id(value: str | None) -> str:
    if not value or value == "-":
        return "-"
    value = value.strip()
    if not _SPAN_ID_RE.match(value):
        return ""
    try:
        parsed = int(value)
    except ValueError:
        return ""
    if parsed <= 0 or parsed >= 2**64:
        return ""
    return str(parsed)


def _parse_sampled(options_part: str) -> bool:
    if not options_part:
        return False
    for option in options_part.split(";"):
        key, sep, value = option.partition("=")
        if sep and key.strip() == "o":
            return value.strip() == "1"
    return False
