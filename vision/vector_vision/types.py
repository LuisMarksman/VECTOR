"""Shared perception data types (mirrors the server's vision schema)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class BoundingBox:
    x: float
    y: float
    w: float
    h: float


@dataclass
class Detection:
    label: str
    confidence: float
    box: BoundingBox | None = None

    def to_dict(self) -> dict:
        data = {"label": self.label, "confidence": self.confidence}
        if self.box is not None:
            data["box"] = asdict(self.box)
        return data


@dataclass
class VisionEvent:
    source: str
    detections: list[Detection] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "detections": [d.to_dict() for d in self.detections],
        }
