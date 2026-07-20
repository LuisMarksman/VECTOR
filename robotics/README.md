# VECTOR Robotics (ROS2)

The ROS2 side of VECTOR: the autonomous mobile base (wheeled chassis), the robot
arm for pick-and-place, the on-board perception "eye", and the bridge that lets
the VECTOR server drive it all over MQTT.

```
                       VECTOR server (MQTT)
                              │
                    ┌─────────▼──────────┐
                    │   vector_bridge    │  MQTT ⇄ ROS2
                    └───┬──────────┬─────┘
              /cmd_vel  │          │  /arm/command
                 ┌──────▼───┐  ┌───▼────────┐   ┌──────────────────┐
                 │vector_base│  │ vector_arm │   │ vector_perception │
                 │  (wheels) │  │  (pick &   │   │   (the "eye")     │
                 │           │  │   place)   │   │  /detections      │
                 └───────────┘  └────────────┘   └──────────────────┘
```

## Packages

| Package              | Node              | Responsibility |
|----------------------|-------------------|----------------|
| `vector_base`        | `base_controller` | `/cmd_vel` → differential-drive wheel speeds |
| `vector_arm`         | `arm_controller`  | Pick/place/home; publishes `/joint_states` |
| `vector_perception`  | `eye_node`        | Camera → object detections (`/detections`) |
| `vector_bridge`      | `mqtt_bridge`     | Bridges server MQTT commands ⇄ ROS2 topics |
| `vector_bringup`     | *(launch only)*   | Brings the whole robot up together |

The bridge is the integration point: it subscribes to
`vector/robot/<id>/cmd` and `vector/arm/cmd` (published by the server's
`RobotManager`) and republishes odometry to `vector/robot/<id>/state`. See
[`../docs/mqtt-topics.md`](../docs/mqtt-topics.md).

## Requirements

- [ROS2 Humble](https://docs.ros.org/en/humble/) (or newer)
- `rclpy`, `geometry_msgs`, `nav_msgs`, `sensor_msgs`, `vision_msgs`, `std_msgs`
- `python3-paho-mqtt` for the bridge
- Optional: [Nav2](https://navigation.ros.org/) for autonomous navigation and
  [MoveIt 2](https://moveit.ros.org/) for arm motion planning

## Build & run

```bash
cd robotics/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash

# Bring up the whole robot, pointing the bridge at the server's broker:
ros2 launch vector_bringup vector.launch.py mqtt_host:=<server-ip> robot_id:=mobile-1
```

### Try individual nodes

```bash
ros2 run vector_base base_controller
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}"

ros2 run vector_arm arm_controller
ros2 topic pub /arm/command std_msgs/msg/String "{data: '{\"action\": \"home\"}'}"
```

## Next steps

These packages are working skeletons with clear extension points:

- `vector_base`: publish real wheel odometry back as `nav_msgs/Odometry`.
- `vector_arm`: replace the stub IK in `arm_controller._ik` with MoveIt 2.
- `vector_perception`: convert `sensor_msgs/Image` with `cv_bridge` and enable
  the YOLO backend in the shared `vision` package.
- Add a Nav2 configuration for autonomous navigation and mapping.
