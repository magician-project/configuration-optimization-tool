"""
Localiser — ros_interface.py

Translates ComputeResult outputs into ROS 2 commands for the localisation node.
"""

from typing import List
from app.models.use_case import ROS2Command

_NODE = "/localisation"


def get_commands(outputs: dict) -> List[ROS2Command]:
    commands: List[ROS2Command] = []

    commands.append(ROS2Command(
        type="param",
        node=_NODE,
        param_name="localisation_approach",
        value=int(outputs.get("localisation_approach", 1)),
    ))
    commands.append(ROS2Command(
        type="param",
        node=_NODE,
        param_name="relaxed_pipeline",
        value=int(outputs.get("relaxed_pipeline", 0)),
    ))
    commands.append(ROS2Command(
        type="param",
        node=_NODE,
        param_name="material_list",
        value=str(outputs.get("material_list", "unspecified")),
    ))

    # Only set mesh_file_path param if a real path was provided
    mesh_path = str(outputs.get("mesh_file_path", "")).strip()
    if mesh_path:
        commands.append(ROS2Command(
            type="param",
            node=_NODE,
            param_name="mesh_file_path",
            value=mesh_path,
        ))

    # Trigger reload after params are set
    commands.append(ROS2Command(
        type="service",
        service="/localisation/reload_config",
        service_type="std_srvs/srv/Trigger",
        request_args={},
    ))

    return commands
