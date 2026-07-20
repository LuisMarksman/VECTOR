"""Object detection.

:class:`MockDetector` emits a deterministic, rotating set of detections so the
pipeline produces sensible events with no model weights. :class:`YoloDetector`
runs a real Ultralytics YOLO model.
"""

from __future__ import annotations

from typing import Any, Protocol

from vector_vision.types import BoundingBox, Detection

_MOCK_LABELS = ["person", "cup", "bottle", "chair", "book"]


class Detector(Protocol):
    def detect(self, frame: Any) -> list[Detection]: ...


class MockDetector:
    """Cycles through a small label set; useful for wiring and demos."""

    def __init__(self) -> None:
        self._tick = 0

    def detect(self, frame: Any) -> list[Detection]:  # noqa: ARG002 - frame unused
        label = _MOCK_LABELS[self._tick % len(_MOCK_LABELS)]
        self._tick += 1
        return [Detection(label=label, confidence=0.9, box=BoundingBox(0.4, 0.4, 0.2, 0.2))]


class YoloDetector:
    """Ultralytics YOLO backend (requires the `yolo` extra + weights)."""

    def __init__(self, model: str = "yolov8n.pt") -> None:
        from ultralytics import YOLO  # lazy import

        self._model = YOLO(model)

    def detect(self, frame: Any) -> list[Detection]:  # pragma: no cover - needs weights
        results = self._model(frame, verbose=False)
        detections: list[Detection] = []
        for result in results:
            names = result.names
            for box in result.boxes:
                cls_id = int(box.cls[0])
                x1, y1, x2, y2 = (float(v) for v in box.xyxy[0])
                detections.append(
                    Detection(
                        label=names.get(cls_id, str(cls_id)),
                        confidence=float(box.conf[0]),
                        box=BoundingBox(x1, y1, x2 - x1, y2 - y1),
                    )
                )
        return detections


def build(backend: str, model: str) -> Detector:
    if backend == "yolo":
        return YoloDetector(model)
    return MockDetector()
