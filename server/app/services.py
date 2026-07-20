"""Service container: constructs and wires the core services once.

FastAPI holds a single :class:`Services` instance on ``app.state`` for the
lifetime of the process. Tests can build their own instance in isolation.
"""

from __future__ import annotations

from app.config import Settings
from app.core.agent import Agent
from app.core.bus import MessageBus
from app.core.home_automation import HomeAutomation
from app.core.llm import get_llm
from app.core.memory import InMemoryMemory
from app.core.planner import HeuristicPlanner
from app.core.robot_manager import RobotManager


class Services:
    """Aggregate of the long-lived services the API depends on."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.bus = MessageBus(
            host=settings.mqtt_host,
            port=settings.mqtt_port,
            base_topic=settings.mqtt_base_topic,
            username=settings.mqtt_username,
            password=settings.mqtt_password,
        )
        self.memory = InMemoryMemory()
        self.llm = get_llm(settings)
        self.planner = HeuristicPlanner()
        self.robots = RobotManager(self.bus)
        self.home = HomeAutomation(self.bus)
        self.agent = Agent(
            llm=self.llm,
            memory=self.memory,
            planner=self.planner,
            robots=self.robots,
            home=self.home,
        )

    def start(self) -> None:
        self.bus.connect()

    def stop(self) -> None:
        self.bus.disconnect()
