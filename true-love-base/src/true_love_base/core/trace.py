# -*- coding: utf-8 -*-
from contextvars import ContextVar

_trace_id: ContextVar[str] = ContextVar('trace_id', default='-')


def get_trace_id() -> str:
    return _trace_id.get()


def set_trace_id(tid: str) -> None:
    _trace_id.set(tid or '-')
