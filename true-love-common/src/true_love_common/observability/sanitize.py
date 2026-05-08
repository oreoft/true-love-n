# -*- coding: utf-8 -*-
"""Shared log sanitization helpers."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

DEFAULT_MAX_TEXT_LENGTH = 2000
DEFAULT_REDACTION = "***"
DEFAULT_SENSITIVE_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "key",
        "openai_key",
        "password",
        "secret",
        "token",
    }
)

_INLINE_SECRET_RE = re.compile(
    r"(?i)\b(access_token|api_key|apikey|authorization|password|secret|token)=([^&\s]+)"
)


def truncate_text(text: str, max_length: int = DEFAULT_MAX_TEXT_LENGTH) -> str:
    if max_length <= 0 or len(text) <= max_length:
        return text
    return f"{text[:max_length]}...[truncated, total {len(text)} chars]"


def sanitize_text(
    text: str,
    *,
    max_length: int = DEFAULT_MAX_TEXT_LENGTH,
    redaction: str = DEFAULT_REDACTION,
) -> str:
    text = _INLINE_SECRET_RE.sub(lambda m: f"{m.group(1)}={redaction}", text)
    return truncate_text(text, max_length)


def sanitize_value(
    value: Any,
    *,
    sensitive_keys: set[str] | frozenset[str] = DEFAULT_SENSITIVE_KEYS,
    max_text_length: int = DEFAULT_MAX_TEXT_LENGTH,
    redaction: str = DEFAULT_REDACTION,
) -> Any:
    if isinstance(value, Mapping):
        return {
            key: redaction if _is_sensitive_key(str(key), sensitive_keys) else sanitize_value(
                item,
                sensitive_keys=sensitive_keys,
                max_text_length=max_text_length,
                redaction=redaction,
            )
            for key, item in value.items()
        }

    if isinstance(value, str):
        return sanitize_text(value, max_length=max_text_length, redaction=redaction)

    if isinstance(value, bytes):
        return f"[binary {len(value)} bytes]"

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [
            sanitize_value(
                item,
                sensitive_keys=sensitive_keys,
                max_text_length=max_text_length,
                redaction=redaction,
            )
            for item in value
        ]

    return value


def sanitize_json_text(
    text: str,
    *,
    sensitive_keys: set[str] | frozenset[str] = DEFAULT_SENSITIVE_KEYS,
    max_text_length: int = DEFAULT_MAX_TEXT_LENGTH,
    redaction: str = DEFAULT_REDACTION,
) -> str:
    try:
        data = json.loads(text)
    except Exception:
        return sanitize_text(text, max_length=max_text_length, redaction=redaction)

    sanitized = sanitize_value(
        data,
        sensitive_keys=sensitive_keys,
        max_text_length=max_text_length,
        redaction=redaction,
    )
    return truncate_text(json.dumps(sanitized, ensure_ascii=False), max_text_length)


def sanitize_headers(headers: Mapping[str, Any]) -> dict[str, Any]:
    return sanitize_value(headers, sensitive_keys=DEFAULT_SENSITIVE_KEYS)


def _is_sensitive_key(key: str, sensitive_keys: set[str] | frozenset[str]) -> bool:
    normalized = key.lower().replace("-", "_")
    if normalized in sensitive_keys:
        return True
    return any(part in normalized for part in ("token", "secret", "password", "authorization", "api_key"))
