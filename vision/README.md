# VECTOR Vision

The eyes of VECTOR. A worker that captures frames, runs perception, and streams
what it sees to the server (which the agent can then reason about, and the robot
arm can act on for pick-and-place).

```
 camera ──► detector ──► tracker ──► publisher ──► server /vision/events
 (mock/cv2) (mock/YOLO)  (centroid)   (httpx)
```

Ships with **mock** backends so it runs and publishes events with no camera and
no model weights — ideal for developing the end-to-end flow.

## Capabilities

| Module          | Purpose |
|-----------------|---------|
| `detector.py`   | Object detection (mock / Ultralytics YOLO) |
| `faces.py`      | Face recognition + enrolment (skeleton) |
| `tracking.py`   | Multi-object centroid tracker |
| `ocr.py`        | Optical character recognition (skeleton) |
| `camera.py`     | Frame source (mock / OpenCV device or stream) |
| `publisher.py`  | Streams `VisionEvent`s to the server |
| `worker.py`     | The capture → detect → track → publish loop |

## Run it

```bash
pip install -r requirements.txt      # just httpx for mock mode
# with the server running (see ../server):
python -m vector_vision
```

You'll see it publishing detections:

```
INFO vector.vision: vision worker started (source=camera0)
INFO vector.vision: saw: person
INFO vector.vision: saw: cup
```

Query what VECTOR currently sees:

```bash
curl http://localhost:8000/vision/events
```

## Real cameras & models

Set the backends via environment variables (see repo-root `.env.example`):

| Variable                   | Default     | Options |
|----------------------------|-------------|---------|
| `VECTOR_CAMERA_BACKEND`    | `mock`      | `mock` · `opencv` |
| `VECTOR_DETECTOR_BACKEND`  | `mock`      | `mock` · `yolo` |
| `VECTOR_CAMERA_SOURCE`     | `0`         | device index or RTSP/HTTP URL |
| `VECTOR_VISION_MODEL`      | `yolov8n.pt`| YOLO weights |
| `VECTOR_VISION_FPS`        | `2.0`       | detections per second |

Install `opencv-python` + `ultralytics` from `requirements.txt`, then switch the
backends. YOLO weights download automatically on first use.
