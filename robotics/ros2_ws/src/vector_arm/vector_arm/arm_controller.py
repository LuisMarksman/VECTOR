"""Robot-arm controller for pick-and-place.

Listens on ``/arm/command`` for JSON commands such as::

    {"action": "pick", "target": {"x": 0.2, "y": 0.0, "z": 0.1}}
    {"action": "place", "target": {"x": 0.0, "y": 0.3, "z": 0.1}}
    {"action": "home"}

and publishes ``sensor_msgs/JointState`` on ``/joint_states``. Inverse
kinematics / trajectory generation is stubbed (``_move_to``) — plug in MoveIt 2
or your own IK solver there. The commands typically originate from the VECTOR
server (via the MQTT bridge) after the vision "eye" locates the object.

Run with::

    ros2 run vector_arm arm_controller
"""

from __future__ import annotations

import json

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String

JOINT_NAMES = ["base", "shoulder", "elbow", "wrist", "gripper"]
HOME_POSITION = [0.0, 0.0, 0.0, 0.0, 0.0]


class ArmController(Node):
    def __init__(self) -> None:
        super().__init__("arm_controller")
        self._position = list(HOME_POSITION)
        self._joint_pub = self.create_publisher(JointState, "joint_states", 10)
        self._cmd_sub = self.create_subscription(String, "arm/command", self._on_command, 10)
        # Publish joint state at 10 Hz.
        self._timer = self.create_timer(0.1, self._publish_state)
        self.get_logger().info("arm_controller ready")

    def _on_command(self, msg: String) -> None:
        try:
            command = json.loads(msg.data)
        except json.JSONDecodeError:
            self.get_logger().warning("ignoring malformed arm command")
            return

        action = command.get("action", "")
        target = command.get("target")
        self.get_logger().info(f"arm command: {action} {target or ''}")

        if action == "home":
            self._move_to(HOME_POSITION)
        elif action == "pick":
            self._move_to(self._ik(target))
            self._set_gripper(closed=True)
        elif action == "place":
            self._move_to(self._ik(target))
            self._set_gripper(closed=False)
        else:
            self.get_logger().warning(f"unknown arm action: {action}")

    # -- motion (stubs) ---------------------------------------------------
    def _ik(self, target: dict | None) -> list[float]:
        """Inverse kinematics: Cartesian target -> joint angles. TODO: MoveIt/IK."""
        if not target:
            return list(self._position)
        # Placeholder mapping so the interface is exercised end to end.
        return [
            target.get("x", 0.0),
            target.get("y", 0.0),
            target.get("z", 0.0),
            0.0,
            self._position[4],
        ]

    def _move_to(self, joints: list[float]) -> None:
        # TODO: interpolate a trajectory and stream to the firmware.
        self._position = list(joints)

    def _set_gripper(self, closed: bool) -> None:
        self._position[-1] = 1.0 if closed else 0.0

    def _publish_state(self) -> None:
        state = JointState()
        state.header.stamp = self.get_clock().now().to_msg()
        state.name = JOINT_NAMES
        state.position = [float(p) for p in self._position]
        self._joint_pub.publish(state)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = ArmController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
