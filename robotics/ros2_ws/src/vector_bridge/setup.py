from setuptools import find_packages, setup

package_name = "vector_bridge"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools", "paho-mqtt"],
    zip_safe=True,
    maintainer="VECTOR contributors",
    maintainer_email="dev@vector.local",
    description="Bridges VECTOR server MQTT commands to/from ROS2 topics.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "mqtt_bridge = vector_bridge.mqtt_bridge:main",
        ],
    },
)
