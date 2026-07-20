"""Smart-home device endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import ServicesDep
from app.models.schemas import HomeDeviceCommand, HomeDeviceState

router = APIRouter()


@router.get("/devices", response_model=list[HomeDeviceState])
def list_devices(services: ServicesDep) -> list[HomeDeviceState]:
    return services.home.devices()


@router.get("/devices/{device_id}", response_model=HomeDeviceState)
def get_device(device_id: str, services: ServicesDep) -> HomeDeviceState:
    return services.home.get_device(device_id)


@router.post("/devices/{device_id}/command")
def command_device(
    device_id: str,
    command: HomeDeviceCommand,
    services: ServicesDep,
) -> dict:
    services.home.command(device_id, command)
    return {"ok": True, "device_id": device_id, "action": command.action}
