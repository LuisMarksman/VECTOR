"""Liveness / readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import ServicesDep
from app.config import get_settings
from app.models.schemas import HealthStatus

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
def health(services: ServicesDep) -> HealthStatus:
    settings = get_settings()
    return HealthStatus(
        status="ok",
        environment=settings.env,
        mqtt_connected=services.bus.connected,
    )
