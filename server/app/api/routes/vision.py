"""Vision ingestion endpoint.

Vision workers (see ``vision/``) POST detection events here, or publish them to
the ``<base>/vision/detections`` MQTT topic. The server keeps the most recent
event per source so the agent and UI can query "what does VECTOR see?".
"""

from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import VisionEvent

router = APIRouter()

# Simple in-memory latest-event cache keyed by source.
_latest: dict[str, VisionEvent] = {}


@router.post("/events")
def ingest(event: VisionEvent) -> dict:
    _latest[event.source] = event
    return {"ok": True, "source": event.source, "count": len(event.detections)}


@router.get("/events", response_model=list[VisionEvent])
def latest() -> list[VisionEvent]:
    return list(_latest.values())
