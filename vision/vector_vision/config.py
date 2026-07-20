"""Vision worker configuration, read from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class VisionConfig:
    server_url: str = "http://localhost:8000"
    camera_source: str = "0"  # device index or stream URL
    source_name: str = "camera0"
    model: str = "yolov8n.pt"
    fps: float = 2.0  # detection frequency

    # Backends: "mock" needs no camera or weights.
    camera_backend: str = "mock"  # mock | opencv
    detector_backend: str = "mock"  # mock | yolo

    @classmethod
    def from_env(cls) -> VisionConfig:
        return cls(
            server_url=os.getenv("VECTOR_SERVER_URL", cls.server_url),
            camera_source=os.getenv("VECTOR_CAMERA_SOURCE", cls.camera_source),
            source_name=os.getenv("VECTOR_VISION_SOURCE", cls.source_name),
            model=os.getenv("VECTOR_VISION_MODEL", cls.model),
            fps=float(os.getenv("VECTOR_VISION_FPS", cls.fps)),
            camera_backend=os.getenv("VECTOR_CAMERA_BACKEND", cls.camera_backend),
            detector_backend=os.getenv("VECTOR_DETECTOR_BACKEND", cls.detector_backend),
        )
