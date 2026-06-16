"""
Grabber — ros_interface.py

The magician_grabber node is a C++ startup-only process: most parameters are
read from launch arguments or a ROS 2 parameter YAML at startup and cannot be
changed via ros2 param set at runtime.

This module therefore returns a single "file" command pointing to the generated
params.yaml and launch_args.txt artifacts, rather than a list of ros2 param set
commands that would be silently ignored at runtime.

The operator should restart the grabber node with:
    ros2 run rclcpp_magician_grabber magician_grabber \\
        --ros-args --params-file <output_dir>/params.yaml
or equivalently use the launch string from launch_args.txt.
"""

from typing import List
from app.models.use_case import ROS2Command

# ROS 2 node name for the Grabber
_NODE = "/magician_grabber"


def get_commands(outputs: dict) -> List[ROS2Command]:
    """
    Returns command descriptors for the grabber.

    Because magician_grabber reads all settings at startup, the only actionable
    commands are references to the generated config artifacts.  A single
    "param" command is emitted for any truly dynamic setting if one exists in
    the future; for now the artifacts path is surfaced as a note.
    """
    commands: List[ROS2Command] = []

    # Surface the params.yaml artifact so the GUI / operator knows where it is
    params_yaml = outputs.get("artifacts", {}).get("params_yaml", "")
    if params_yaml:
        commands.append(ROS2Command(
            type="note",
            node=_NODE,
            param_name="params_yaml_path",
            value=params_yaml,
        ))

    launch_args = outputs.get("artifacts", {}).get("launch_args", "")
    if launch_args:
        commands.append(ROS2Command(
            type="note",
            node=_NODE,
            param_name="launch_args_path",
            value=launch_args,
        ))

    # Preserve legacy fields so existing result consumers are not broken
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

    return commands
