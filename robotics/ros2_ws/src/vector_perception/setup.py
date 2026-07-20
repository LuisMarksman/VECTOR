from setuptools import find_packages, setup

package_name = "vector_perception"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="VECTOR contributors",
    maintainer_email="dev@vector.local",
    description='The robot "eye": object detection feeding navigation and the arm.',
    license="MIT",
    entry_points={
        "console_scripts": [
            "eye_node = vector_perception.eye_node:main",
        ],
    },
)
