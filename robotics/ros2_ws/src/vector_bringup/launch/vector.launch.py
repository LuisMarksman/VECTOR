"""Bring up the full VECTOR robot: base, arm, perception and the server bridge.

Usage::

    ros2 launch vector_bringup vector.launch.py mqtt_host:=192.168.1.10 robot_id:=mobile-1
"""

from __future__ import annotations

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    mqtt_host = LaunchConfiguration("mqtt_host")
    robot_id = LaunchConfiguration("robot_id")

    return LaunchDescription(
        [
            DeclareLaunchArgument("mqtt_host", default_value="localhost"),
            DeclareLaunchArgument("robot_id", default_value="mobile-1"),
            Node(
                package="vector_base",
                executable="base_controller",
                name="base_controller",
                output="screen",
            ),
            Node(
                package="vector_arm",
                executable="arm_controller",
                name="arm_controller",
                output="screen",
            ),
            Node(
                package="vector_perception",
                executable="eye_node",
                name="eye_node",
                output="screen",
            ),
            Node(
                package="vector_bridge",
                executable="mqtt_bridge",
                name="mqtt_bridge",
                output="screen",
                parameters=[{"mqtt_host": mqtt_host, "robot_id": robot_id}],
            ),
        ]
    )
