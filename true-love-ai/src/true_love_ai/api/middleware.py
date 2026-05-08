#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""FastAPI middleware compatibility exports."""

from true_love_common.integrations.fastapi import HttpLoggingMiddleware as LoggingMiddleware
from true_love_common.integrations.fastapi import HttpLoggingMiddleware

__all__ = ["HttpLoggingMiddleware", "LoggingMiddleware"]
