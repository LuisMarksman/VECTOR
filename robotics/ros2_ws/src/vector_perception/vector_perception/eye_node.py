"""The robot "eye" node.

Subscribes to the camera image stream, runs object detection, and publishes
``vision_msgs/Detection2DArray`` on ``/detections`` — consumed by navigation
(obstacles) and the arm (pick targets). The heavy detection logic lives in the
standalone ``vision`` package (``vector_vision.detector``); this node is the
ROS2 adapter around it.

Run with::

    ros2 run vector_perception eye_node
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose


class EyeNode(Node):
    def __init__(self) -> None:
        super().__init__("eye_node")
        self.declare_parameter("image_topic", "/camera/image_raw")
        image_topic = self.get_parameter("image_topic").value

        self._detections_pub = self.create_publisher(Detection2DArray, "detections", 10)
        self._image_sub = self.create_subscription(Image, image_topic, self._on_image, 10)

        # Lazily created so the node starts even before weights are downloaded.
        self._detector = None
        self.get_logger().info(f"eye_node ready (subscribing to {image_topic})")

    def _ensure_detector(self):
        if self._detector is None:
            # Reuse the shared vision package. Falls back to the mock detector
            # when model weights / OpenCV are unavailable.
            from vector_vision.detector import build

            self._detector = build("mock", "yolov8n.pt")
        return self._detector

    def _on_image(self, msg: Image) -> None:
        detector = self._ensure_detector()
        # TODO: convert `msg` (sensor_msgs/Image) to an array with cv_bridge.
        frame = None
        detections = detector.detect(frame)

        out = Detection2DArray()
        out.header = msg.header
        for det in detections:
            d = Detection2D()
            hyp = ObjectHypothesisWithPose()
            hyp.hypothesis.class_id = det.label
            hyp.hypothesis.score = det.confidence
            d.results.append(hyp)
            out.detections.append(d)
        self._detections_pub.publish(out)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = EyeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
