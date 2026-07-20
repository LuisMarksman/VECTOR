"""Coordinates the mobile robot(s) and the robot arm over the message bus.

The manager keeps a lightweight, in-memory view of each robot's last known
state (updated from ``.../state`` topics) and dispatches commands to
``.../cmd`` topics. It knows nothing about motor control — that lives in the
robot's own ROS2 nodes and firmware.
"""

from __future__ import annotations

import logging

from app.core.bus import MessageBus
from app.models.schemas import ArmCommand, RobotCommand, RobotState

logger = logging.getLogger("vector.robots")


class RobotManager:
    def __init__(self, bus: MessageBus) -> None:
        self._bus = bus
        self._states: dict[str, RobotState] = {}
        # Listen for state reports from every robot.
        bus.subscribe(bus.topic("robot", "+", "state"), self._on_state)

    # -- commands ---------------------------------------------------------
    def dispatch(self, robot_id: str, command: RobotCommand) -> None:
        topic = self._bus.topic("robot", robot_id, "cmd")
        self._bus.publish(topic, command.model_dump())
        logger.info("robot %s <- %s", robot_id, command.action)

    def dispatch_arm(self, command: ArmCommand) -> None:
        self._bus.publish(self._bus.topic("arm", "cmd"), command.model_dump())
        logger.info("arm <- %s", command.action)

    # -- state ------------------------------------------------------------
    def get_state(self, robot_id: str) -> RobotState:
        return self._states.get(robot_id, RobotState(robot_id=robot_id, online=False))

    def all_states(self) -> list[RobotState]:
        return list(self._states.values())

    def _on_state(self, topic: str, payload: dict) -> None:
        # topic: <base>/robot/<id>/state
        robot_id = topic.split("/")[-2]
        self._states[robot_id] = RobotState(robot_id=robot_id, **payload)
