"""Smart-home control: lights, switches, sensors and cameras over MQTT.

Devices publish their state to ``<base>/home/<id>/state`` and accept commands
on ``<base>/home/<id>/set``. This mirrors the conventions used by common
smart-home stacks (e.g. Home Assistant / Tasmota), which makes bridging to
existing hardware straightforward.
"""

from __future__ import annotations

import logging

from app.core.bus import MessageBus
from app.models.schemas import HomeDeviceCommand, HomeDeviceState

logger = logging.getLogger("vector.home")


class HomeAutomation:
    def __init__(self, bus: MessageBus) -> None:
        self._bus = bus
        self._devices: dict[str, HomeDeviceState] = {}
        bus.subscribe(bus.topic("home", "+", "state"), self._on_state)

    # -- commands ---------------------------------------------------------
    def command(self, device_id: str, command: HomeDeviceCommand) -> None:
        topic = self._bus.topic("home", device_id, "set")
        self._bus.publish(topic, command.model_dump(exclude_none=True))
        logger.info("home %s <- %s %s", device_id, command.action, command.value or "")

    # -- state ------------------------------------------------------------
    def get_device(self, device_id: str) -> HomeDeviceState:
        return self._devices.get(device_id, HomeDeviceState(device_id=device_id, online=False))

    def devices(self) -> list[HomeDeviceState]:
        return list(self._devices.values())

    def _on_state(self, topic: str, payload: dict) -> None:
        device_id = topic.split("/")[-2]
        payload.setdefault("device_id", device_id)
        self._devices[device_id] = HomeDeviceState(**payload)
