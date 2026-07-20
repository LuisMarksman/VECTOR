"""The vision worker loop: capture -> detect -> track -> publish."""

from __future__ import annotations

import logging
import time

from vector_vision import camera as camera_mod
from vector_vision import detector as detector_mod
from vector_vision.config import VisionConfig
from vector_vision.publisher import ServerPublisher
from vector_vision.tracking import CentroidTracker
from vector_vision.types import VisionEvent

logger = logging.getLogger("vector.vision")


class VisionWorker:
    def __init__(self, config: VisionConfig | None = None) -> None:
        self.config = config or VisionConfig.from_env()
        self.camera = camera_mod.build(self.config.camera_backend, self.config.camera_source)
        self.detector = detector_mod.build(self.config.detector_backend, self.config.model)
        self.tracker = CentroidTracker()
        self.publisher = ServerPublisher(self.config.server_url)

    def step(self) -> VisionEvent:
        """Run a single capture/detect/publish cycle and return the event."""
        frame = self.camera.read()
        detections = self.detector.detect(frame)
        self.tracker.update(detections)
        event = VisionEvent(source=self.config.source_name, detections=detections)
        self.publisher.publish(event)
        return event

    def run(self, max_iterations: int | None = None) -> None:
        interval = 1.0 / self.config.fps if self.config.fps > 0 else 0.0
        logger.info("vision worker started (source=%s)", self.config.source_name)
        count = 0
        try:
            while max_iterations is None or count < max_iterations:
                event = self.step()
                labels = ", ".join(d.label for d in event.detections) or "nothing"
                logger.info("saw: %s", labels)
                count += 1
                if interval:
                    time.sleep(interval)
        except KeyboardInterrupt:
            pass
        finally:
            self.close()

    def close(self) -> None:
        self.camera.release()
        self.publisher.close()
