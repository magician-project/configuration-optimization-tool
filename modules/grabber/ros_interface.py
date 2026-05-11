"""
Grabber — ros_interface.py

Translates ComputeResult outputs into a list of ROS 2 commands
(ros2 param set / ros2 service call) to apply to the running
magician_grabber node.

Only str, int, and float values are passed to ROS 2.
"""

from typing import List
from app.models.use_case import ROS2Command

# ROS 2 node name for the Grabber
_NODE = "/magician_grabber"


def get_commands(outputs: dict) -> List[ROS2Command]:
    """
    Given the flat outputs dict from compute.py, return the ordered list of
    ROS 2 commands to apply.
    """
    commands: List[ROS2Command] = []

    # Multi-arm mode
    commands.append(ROS2Command(
        type="param",
        node=_NODE,
        param_name="multi_arm_mode",
        value=int(outputs.get("multi_arm_mode", 0)),
    ))
    commands.append(ROS2Command(
        type="param",
        node=_NODE,
        param_name="num_arms",
        value=int(outputs.get("num_arms", 1)),
    ))

    # Camera type
    commands.append(ROS2Command(
        type="param",
        node=_NODE,
        param_name="camera_type",
        value=str(outputs.get("camera_type", "standard")),
    ))
    if "camera_spec" in outputs:
        commands.append(ROS2Command(
            type="param",
            node=_NODE,
            param_name="camera_spec",
            value=str(outputs["camera_spec"]),
        ))

    # Extra sensors
    commands.append(ROS2Command(
        type="param",
        node=_NODE,
        param_name="extra_sensor_mask",
        value=int(outputs.get("extra_sensor_mask", 0)),
    ))

    # Lighting
    commands.append(ROS2Command(
        type="param",
        node=_NODE,
        param_name="extra_lighting_enabled",
        value=int(outputs.get("extra_lighting", 0)),
    ))

    return commands
