"""
Tactile Sensor — ros_interface.py

Translates ComputeResult outputs into ROS 2 commands for the
tactile_classifier_system node.

The key command is setting the model_path parameter so the node loads
the freshly trained model on its next startup or reload.
"""

from typing import List
from app.models.use_case import ROS2Command

_NODE = "/tactile_classifier_system"


def get_commands(outputs: dict) -> List[ROS2Command]:
    commands: List[ROS2Command] = []

    model_path = str(outputs.get("model_path", "")).strip()
    if model_path:
        commands.append(ROS2Command(
            type="param",
            node=_NODE,
            param_name="model_path",
            value=model_path,
        ))

    commands.append(ROS2Command(
        type="param",
        node=_NODE,
        param_name="material_list",
        value=str(outputs.get("materials", "unspecified")),
    ))
    commands.append(ROS2Command(
        type="param",
        node=_NODE,
        param_name="defect_types",
        value=str(outputs.get("defect_types", "unspecified")),
    ))

    # Trigger model reload
    commands.append(ROS2Command(
        type="service",
        service="/tactile_classifier_system/reload_model",
        service_type="std_srvs/srv/Trigger",
        request_args={},
    ))

    return commands
