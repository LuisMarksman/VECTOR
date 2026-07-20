"""Face recognition (skeleton).

Provides the interface the worker uses. The real implementation should embed
faces (e.g. with `face_recognition` or an ONNX model) and match them against an
enrolled gallery. Kept as a stub so the package installs without heavy deps.
"""

from __future__ import annotations

from typing import Any

from vector_vision.types import Detection


class FaceRecognizer:
    def __init__(self, gallery: dict[str, Any] | None = None) -> None:
        self.gallery = gallery or {}

    def recognize(self, frame: Any) -> list[Detection]:  # noqa: ARG002
        """Return recognised faces as detections labelled with the person name."""
        # TODO: detect faces, compute embeddings, match against self.gallery.
        return []

    def enroll(self, name: str, frame: Any) -> None:
        """Add a person's face to the gallery."""
        self.gallery[name] = frame
