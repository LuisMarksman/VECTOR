"""Streams vision events to the VECTOR server."""

from __future__ import annotations

import logging

import httpx

from vector_vision.types import VisionEvent

logger = logging.getLogger("vector.vision.publisher")


class ServerPublisher:
    def __init__(self, base_url: str, timeout: float = 5.0) -> None:
        self._url = base_url.rstrip("/") + "/vision/events"
        self._http = httpx.Client(timeout=timeout)

    def publish(self, event: VisionEvent) -> None:
        try:
            self._http.post(self._url, json=event.to_dict())
        except httpx.HTTPError as exc:
            logger.warning("failed to publish vision event: %s", exc)

    def close(self) -> None:
        self._http.close()
