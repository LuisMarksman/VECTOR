"""MQTT message bus — the nervous system that links the server to devices.

The bus is intentionally tolerant: if ``paho-mqtt`` is not installed or no
broker is reachable, it degrades to a disabled state that logs publishes
instead of raising. That keeps the API and the test-suite runnable on a laptop
with no broker, while the exact same code talks to real hardware in production.

Topic convention (see ``docs/mqtt-topics.md``)::

    <base>/robot/<id>/cmd      server -> robot
    <base>/robot/<id>/state    robot  -> server
    <base>/home/<id>/set       server -> device
    <base>/home/<id>/state     device -> server
    <base>/vision/detections   vision -> server
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("vector.bus")

try:  # paho is optional so the core stays importable without a broker.
    import paho.mqtt.client as mqtt

    _HAS_PAHO = True
except ImportError:  # pragma: no cover - exercised only when paho is absent
    mqtt = None  # type: ignore[assignment]
    _HAS_PAHO = False

Handler = Callable[[str, dict], None]


class MessageBus:
    """A thin, fault-tolerant wrapper around an MQTT client."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 1883,
        base_topic: str = "vector",
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.base_topic = base_topic.rstrip("/")
        self._username = username
        self._password = password
        self._client: Any = None
        self._handlers: dict[str, Handler] = {}
        self._connected = False

    # -- lifecycle --------------------------------------------------------
    def connect(self) -> None:
        """Attempt to connect to the broker. Never raises on failure."""
        if not _HAS_PAHO:
            logger.warning("paho-mqtt not installed; message bus is disabled")
            return
        try:
            self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            if self._username:
                self._client.username_pw_set(self._username, self._password)
            self._client.on_connect = self._on_connect
            self._client.on_message = self._on_message
            self._client.connect(self.host, self.port, keepalive=60)
            self._client.loop_start()
            logger.info("MQTT bus connecting to %s:%s", self.host, self.port)
        except OSError as exc:  # broker unreachable
            logger.warning("MQTT broker unavailable (%s); running degraded", exc)
            self._client = None

    def disconnect(self) -> None:
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    # -- pub/sub ----------------------------------------------------------
    def topic(self, *parts: str) -> str:
        """Build a namespaced topic, e.g. ``topic("robot", id, "cmd")``."""
        return "/".join([self.base_topic, *[p.strip("/") for p in parts]])

    def publish(self, topic: str, payload: dict) -> None:
        """Publish a JSON payload. No-op (logged) when the bus is disabled."""
        message = json.dumps(payload)
        if self._client is None:
            logger.debug("[bus disabled] would publish %s -> %s", topic, message)
            return
        self._client.publish(topic, message, qos=0)

    def subscribe(self, topic: str, handler: Handler) -> None:
        """Register a handler for a topic (supports MQTT wildcards)."""
        self._handlers[topic] = handler
        if self._client is not None:
            self._client.subscribe(topic)

    # -- callbacks --------------------------------------------------------
    def _on_connect(self, client: Any, _userdata: Any, _flags: Any, _rc: Any, *_: Any) -> None:
        self._connected = True
        logger.info("MQTT bus connected")
        for topic in self._handlers:
            client.subscribe(topic)

    def _on_message(self, _client: Any, _userdata: Any, msg: Any) -> None:
        try:
            payload = json.loads(msg.payload.decode() or "{}")
        except (ValueError, UnicodeDecodeError):
            logger.warning("dropping non-JSON message on %s", msg.topic)
            return
        for pattern, handler in self._handlers.items():
            if _topic_matches(pattern, msg.topic):
                handler(msg.topic, payload)


def _topic_matches(pattern: str, topic: str) -> bool:
    """Minimal MQTT topic matcher supporting ``+`` and ``#`` wildcards."""
    p_parts = pattern.split("/")
    t_parts = topic.split("/")
    for i, p in enumerate(p_parts):
        if p == "#":
            return True
        if i >= len(t_parts):
            return False
        if p != "+" and p != t_parts[i]:
            return False
    return len(p_parts) == len(t_parts)
