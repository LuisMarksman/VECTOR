"""FastAPI application factory and entrypoint.

Run in development with::

    uvicorn app.main:app --reload

The app owns a single :class:`~app.services.Services` container on
``app.state`` and manages the message-bus connection over its lifespan.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import api_router
from app.config import get_settings
from app.logging_config import configure_logging
from app.services import Services


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    services = Services(settings)
    services.start()
    app.state.services = services
    try:
        yield
    finally:
        services.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="VECTOR Server",
        version=__version__,
        summary="Reasoning, planning and orchestration brain for VECTOR.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)

    @app.get("/", tags=["system"])
    def root() -> dict:
        return {
            "name": "VECTOR",
            "tagline": "Virtual Engine for Control, Tasks & Operational Robotics",
            "version": __version__,
            "docs": "/docs",
        }

    return app


app = create_app()
