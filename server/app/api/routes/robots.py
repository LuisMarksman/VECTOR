"""Robot fleet + arm control endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import ServicesDep
from app.models.schemas import ArmCommand, RobotCommand, RobotState

router = APIRouter()


@router.get("", response_model=list[RobotState])
def list_robots(services: ServicesDep) -> list[RobotState]:
    return services.robots.all_states()


@router.get("/{robot_id}", response_model=RobotState)
def get_robot(robot_id: str, services: ServicesDep) -> RobotState:
    return services.robots.get_state(robot_id)


@router.post("/{robot_id}/command")
def command_robot(robot_id: str, command: RobotCommand, services: ServicesDep) -> dict:
    services.robots.dispatch(robot_id, command)
    return {"ok": True, "robot_id": robot_id, "action": command.action}


@router.post("/arm/command")
def command_arm(command: ArmCommand, services: ServicesDep) -> dict:
    services.robots.dispatch_arm(command)
    return {"ok": True, "action": command.action}
