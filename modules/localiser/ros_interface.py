"""
Localiser — ros_interface.py

Translates compute.py outputs into ROS 2 commands for the /localisation
broadcaster. Per COT_LOCALISER.md the node has no registration service or
reload action, so most entries here are operator-facing notes rather than
live `ros2 param set` calls.
"""

from typing import List
from app.models.use_case import ROS2Command

_NODE = "/localisation"


def get_commands(outputs: dict) -> List[ROS2Command]:
    commands: List[ROS2Command] = []

    params_yaml = outputs.get("artifacts", {}).get("params_yaml", "")
    if params_yaml:
        commands.append(ROS2Command(
            type="note",
            node=_NODE,
            param_name="params_yaml_path",
            value=params_yaml,
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
