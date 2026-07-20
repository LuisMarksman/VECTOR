"""A minimal centroid tracker.

Assigns stable integer IDs to detections across frames by nearest-centroid
matching. Pure-Python (no numpy) so it runs anywhere; swap for a Kalman/SORT
tracker when you need robustness to occlusion.
"""

from __future__ import annotations

from dataclasses import dataclass

from vector_vision.types import Detection


@dataclass
class Track:
    id: int
    label: str
    centroid: tuple[float, float]
    misses: int = 0


class CentroidTracker:
    def __init__(self, max_distance: float = 0.1, max_misses: int = 5) -> None:
        self._max_distance = max_distance
        self._max_misses = max_misses
        self._tracks: dict[int, Track] = {}
        self._next_id = 0

    def update(self, detections: list[Detection]) -> dict[int, Track]:
        centroids = [(_centroid(d), d) for d in detections if d.box is not None]
        unmatched = set(self._tracks)

        for centroid, det in centroids:
            match_id = self._nearest(centroid, unmatched)
            if match_id is None:
                match_id = self._next_id
                self._next_id += 1
                self._tracks[match_id] = Track(match_id, det.label, centroid)
            else:
                track = self._tracks[match_id]
                track.centroid = centroid
                track.label = det.label
                track.misses = 0
                unmatched.discard(match_id)

        # Age out tracks we didn't see this frame.
        for track_id in list(unmatched):
            self._tracks[track_id].misses += 1
            if self._tracks[track_id].misses > self._max_misses:
                del self._tracks[track_id]

        return dict(self._tracks)

    def _nearest(self, centroid: tuple[float, float], candidates: set[int]) -> int | None:
        best_id, best_dist = None, self._max_distance
        for track_id in candidates:
            dist = _distance(centroid, self._tracks[track_id].centroid)
            if dist <= best_dist:
                best_id, best_dist = track_id, dist
        return best_id


def _centroid(det: Detection) -> tuple[float, float]:
    box = det.box
    assert box is not None
    return (box.x + box.w / 2, box.y + box.h / 2)


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
