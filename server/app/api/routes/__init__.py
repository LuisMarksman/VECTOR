"""API route aggregation."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import assistant, health, home, robots, vision

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(assistant.router, prefix="/assistant", tags=["assistant"])
api_router.include_router(robots.router, prefix="/robots", tags=["robots"])
api_router.include_router(home.router, prefix="/home", tags=["home"])
api_router.include_router(vision.router, prefix="/vision", tags=["vision"])
