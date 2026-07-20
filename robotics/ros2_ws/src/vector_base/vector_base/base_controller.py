"""Differential-drive base controller.

Subscribes to ``/cmd_vel`` (``geometry_msgs/Twist``), converts the requested
linear/angular velocity into left/right wheel speeds using the robot's wheel
geometry, and publishes them on ``/wheel_cmd`` (``std_msgs/Float32MultiArray``,
``[left, right]`` in rad/s). The ESP32 firmware subscribes to that topic (via
the MQTT bridge) and drives the motors.

Run with::

    ros2 run vector_base base_controller
"""

from __future__ import annotations

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray


class BaseController(Node):
    def __init__(self) -> None:
        super().__init__("base_controller")

        # Physical geometry — override via ROS parameters.
        self.declare_parameter("wheel_radius", 0.033)  # metres
        self.declare_parameter("wheel_separation", 0.16)  # metres
        self.wheel_radius = self.get_parameter("wheel_radius").value
        self.wheel_separation = self.get_parameter("wheel_separation").value

        self._wheel_pub = self.create_publisher(Float32MultiArray, "wheel_cmd", 10)
        self._cmd_sub = self.create_subscription(Twist, "cmd_vel", self._on_cmd_vel, 10)
        self.get_logger().info("base_controller ready")

    def _on_cmd_vel(self, msg: Twist) -> None:
        v = msg.linear.x  # m/s
        w = msg.angular.z  # rad/s
        # Differential-drive inverse kinematics.
        left = (v - w * self.wheel_separation / 2.0) / self.wheel_radius
        right = (v + w * self.wheel_separation / 2.0) / self.wheel_radius
        self._wheel_pub.publish(Float32MultiArray(data=[left, right]))


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = BaseController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
