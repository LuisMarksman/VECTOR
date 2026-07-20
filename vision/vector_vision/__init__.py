"""VECTOR computer-vision worker.

Captures frames, runs perception (object detection, faces, tracking, OCR) and
streams the results to the VECTOR server / MQTT bus. Like the voice client it
ships with dependency-free *mock* backends so the pipeline runs and publishes
events without a camera or model weights.
"""

__version__ = "0.1.0"
