"""MQTT <-> ROS2 bridge.

This node is what lets the VECTOR server command the physical robot without
knowing anything about ROS2. It:

* subscribes to ``vector/robot/<id>/cmd`` on MQTT and turns commands into ROS2
  ``/cmd_vel`` (``geometry_msgs/Twist``) messages,
* forwards ``vector/arm/cmd`` to the ROS2 ``/arm/command`` topic,
* republishes ROS2 ``/odom`` back to ``vector/robot/<id>/state`` on MQTT so the
  server's RobotManager can track the robot.

Run with::

    ros2 run vector_bridge mqtt_bridge --ros-args -p robot_id:=mobile-1
"""

from __future__ import annotations

import json

import paho.mqtt.client as mqtt
import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from std_msgs.msg import String


class MqttBridge(Node):
    def __init__(self) -> None:
        super().__init__("mqtt_bridge")
        self.declare_parameter("mqtt_host", "localhost")
        self.declare_parameter("mqtt_port", 1883)
        self.declare_parameter("robot_id", "mobile-1")
        self.declare_parameter("base_topic", "vector")
        self.declare_parameter("linear_speed", 0.2)
        self.declare_parameter("angular_speed", 0.5)

        self.robot_id = self.get_parameter("robot_id").value
        self.base_topic = self.get_parameter("base_topic").value
        self.linear_speed = self.get_parameter("linear_speed").value
        self.angular_speed = self.get_parameter("angular_speed").value

        # ROS2 publishers into the robot.
        self._cmd_vel_pub = self.create_publisher(Twist, "cmd_vel", 10)
        self._arm_pub = self.create_publisher(String, "arm/command", 10)
        # ROS2 subscription for state we report back to the server.
        self.create_subscription(Odometry, "odom", self._on_odom, 10)

        # MQTT client toward the VECTOR server.
        host = self.get_parameter("mqtt_host").value
        port = self.get_parameter("mqtt_port").value
        self._mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._mqtt.on_connect = self._on_mqtt_connect
        self._mqtt.on_message = self._on_mqtt_message
        self._mqtt.connect(host, port, keepalive=60)
        self._mqtt.loop_start()
        self.get_logger().info(f"mqtt_bridge ready for robot '{self.robot_id}' via {host}:{port}")

    # -- MQTT -> ROS2 -----------------------------------------------------
    def _topic(self, *parts: str) -> str:
        return "/".join([self.base_topic, *parts])

    def _on_mqtt_connect(self, client, _userdata, _flags, _rc, *_args) -> None:
        client.subscribe(self._topic("robot", self.robot_id, "cmd"))
        client.subscribe(self._topic("arm", "cmd"))

    def _on_mqtt_message(self, _client, _userdata, msg) -> None:
        try:
            payload = json.loads(msg.payload.decode() or "{}")
        except ValueError:
            self.get_logger().warning(f"bad payload on {msg.topic}")
            return

        if msg.topic.endswith("/arm/cmd"):
            self._arm_pub.publish(String(data=json.dumps(payload)))
            return

        # Robot base command: map a high-level action to a velocity.
        action = payload.get("action", "stop")
        twist = Twist()
        if action in ("navigate", "deliver", "clean"):
            twist.linear.x = float(self.linear_speed)
        elif action == "turn":
            twist.angular.z = float(self.angular_speed)
        # "stop" / "dock" leave the zero-initialised twist.
        self._cmd_vel_pub.publish(twist)
        self.get_logger().info(f"{action} -> cmd_vel(lin={twist.linear.x}, ang={twist.angular.z})")

    # -- ROS2 -> MQTT -----------------------------------------------------
    def _on_odom(self, msg: Odometry) -> None:
        pose = msg.pose.pose
        state = {
            "online": True,
            "status": "moving",
            "pose": {
                "x": pose.position.x,
                "y": pose.position.y,
                "yaw": pose.orientation.z,
            },
        }
        self._mqtt.publish(self._topic("robot", self.robot_id, "state"), json.dumps(state))

    def destroy_node(self) -> bool:
        self._mqtt.loop_stop()
        self._mqtt.disconnect()
        return super().destroy_node()


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = MqttBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
