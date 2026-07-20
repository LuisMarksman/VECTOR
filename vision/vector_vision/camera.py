"""Frame sources.

:class:`MockCamera` yields ``None`` frames (a placeholder) so the pipeline runs
with no hardware; the mock detector doesn't inspect frame contents.
:class:`OpenCVCamera` reads real frames from a device or stream.
"""

from __future__ import annotations

from typing import Any, Protocol


class Camera(Protocol):
    def read(self) -> Any:
        """Return the next frame (or ``None`` for the mock source)."""
        ...

    def release(self) -> None: ...


class MockCamera:
    def __init__(self, source: str = "0") -> None:
        self.source = source

    def read(self) -> Any:
        return None

    def release(self) -> None:
        pass


class OpenCVCamera:
    """Reads frames via OpenCV (requires the `opencv-python` extra)."""

    def __init__(self, source: str = "0") -> None:
        import cv2  # lazy import

        # A digit means a local device index; otherwise treat it as a URL/path.
        cam_id: int | str = int(source) if source.isdigit() else source
        self._cap = cv2.VideoCapture(cam_id)

    def read(self) -> Any:  # pragma: no cover - requires a camera
        ok, frame = self._cap.read()
        return frame if ok else None

    def release(self) -> None:  # pragma: no cover - requires a camera
        self._cap.release()


def build(backend: str, source: str) -> Camera:
    if backend == "opencv":
        return OpenCVCamera(source)
    return MockCamera(source)
