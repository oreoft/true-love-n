# -*- coding: utf-8 -*-
"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from true_love_common.integrations.fastapi import HttpLoggingMiddleware, setup_exception_handlers

from true_love_base.api.routes import router


def create_app() -> FastAPI:
    application = FastAPI(title="True Love Base", version="0.2.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(
        HttpLoggingMiddleware,
        service_name="tl-base",
        skip_paths={"/ping"},
        max_response_body_chars=200,
    )
    setup_exception_handlers(application)
    application.include_router(router)
    return application


app = create_app()
