"""
Localiser — ros_interface.py

The /localisation node's section-4 settings (setup, database_file, mesh_path,
robot_base_link, robot_ee_link, mesh_link, and the dynamic-mode slider
settings) are regular ROS 2 node parameters — COT_LOCALISER.md does not
document them as startup-only/read-only, so they are fired as live
`ros2 param set` commands, matching the contract in modules/README.md.
Per COT_LOCALISER.md section 3 there is currently no registration
service/action, so the remaining process caveats (missing setup, mesh
requirement, registration reminder, database_file quirk) are still
surfaced as operator-facing notes rather than commands.
"""

from typing import List
from app.models.use_case import ROS2Command

_NODE = "/localisation"


def get_commands(outputs: dict) -> List[ROS2Command]:
    commands: List[ROS2Command] = []

    # ── Live ros2 param set commands (section 4 of COT_LOCALISER.md) ────────
    commands.append(ROS2Command(
        type="param", node=_NODE, param_name="setup",
        value=str(outputs.get("setup", "")),
    ))
    commands.append(ROS2Command(
        type="param", node=_NODE, param_name="database_file",
        value=str(outputs.get("database_file", "")),
    ))
    commands.append(ROS2Command(
        type="param", node=_NODE, param_name="mesh_path",
        value=str(outputs.get("mesh_path", "")),
    ))
    commands.append(ROS2Command(
        type="param", node=_NODE, param_name="robot_base_link",
        value=str(outputs.get("robot_base_link", "base_link")),
    ))
    commands.append(ROS2Command(
        type="param", node=_NODE, param_name="robot_ee_link",
        value=str(outputs.get("robot_ee_link", "tcp")),
    ))
    commands.append(ROS2Command(
        type="param", node=_NODE, param_name="mesh_link",
        value=str(outputs.get("mesh_link", "fender")),
    ))

    motion_mode = str(outputs.get("motion_mode", "static"))
    # Must be set explicitly — otherwise switching static<->dynamic never
    # reaches the node, it would just silently keep its previous mode.
    commands.append(ROS2Command(
        type="param", node=_NODE, param_name="mode",
        value=motion_mode,
    ))
    if motion_mode == "dynamic":
        commands.append(ROS2Command(
            type="param", node=_NODE, param_name="slider_topic",
            value=str(outputs.get("slider_topic", "/slider/position_y")),
        ))
        commands.append(ROS2Command(
            type="param", node=_NODE, param_name="slider_bias",
            value=float(outputs.get("slider_bias", 0.0)),
        ))
        commands.append(ROS2Command(
            type="param", node=_NODE, param_name="publish_rate_hz",
            value=float(outputs.get("publish_rate_hz", 30.0)),
        ))

    # ── Operator-facing notes (process caveats — see module docstring) ──────
    params_yaml = outputs.get("params_yaml_path", "")
    if params_yaml:
        commands.append(ROS2Command(
            type="note",
            node=_NODE,
            param_name="params_yaml_path",
            value=params_yaml,
        ))

    if outputs.get("setup_missing"):
        commands.append(ROS2Command(
            type="note",
            node=_NODE,
            param_name="setup_missing",
            value=(
                "No setup name was provided, so the broadcaster has no calibration entry "
                "to select. q_local_setup must be filled in before deploy."
            ),
        ))

    setup = str(outputs.get("setup", "")).strip()
    if setup and not outputs.get("setup_registered"):
        commands.append(ROS2Command(
            type="note",
            node=_NODE,
            param_name="setup_registration_reminder",
            value=(
                f"Confirm setup '{setup}' has been registered (CAD/TCP point pairs "
                "collected, transform saved) before deploy — COT cannot verify this."
            ),
        ))

    if outputs.get("mesh_required"):
        commands.append(ROS2Command(
            type="note",
            node=_NODE,
            param_name="mesh_required",
            value="A mesh path is required to register a new setup, but none was provided.",
        ))

    database_file = outputs.get("database_file", "")
    if database_file:
        commands.append(ROS2Command(
            type="note",
            node=_NODE,
            param_name="database_file_caveat",
            value=(
                f"database_file={database_file} is included in the generated config, but the "
                "current registrator implementation always writes to the package-default "
                "database regardless of this value."
            ),
        ))

    return commands
