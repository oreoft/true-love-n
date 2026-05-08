# -*- coding: utf-8 -*-
"""Trace helpers re-exported from true-love-common."""

from true_love_common.observability.trace import (
    GCP_TRACE_HEADER,
    TraceContext,
    clear_trace_context,
    get_gcp_trace_header,
    get_span_id,
    get_trace_context,
    get_trace_id,
    is_trace_sampled,
    new_span_id,
    new_trace_id,
    set_trace_context,
    set_trace_from_gcp_header,
    set_trace_id,
)

__all__ = [
    "GCP_TRACE_HEADER",
    "TraceContext",
    "clear_trace_context",
    "get_gcp_trace_header",
    "get_span_id",
    "get_trace_context",
    "get_trace_id",
    "is_trace_sampled",
    "new_span_id",
    "new_trace_id",
    "set_trace_context",
    "set_trace_from_gcp_header",
    "set_trace_id",
]
