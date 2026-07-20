from setuptools import find_packages, setup

package_name = "vector_arm"

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
    description="Pick-and-place controller for the VECTOR robot arm.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "arm_controller = vector_arm.arm_controller:main",
        ],
    },
)
