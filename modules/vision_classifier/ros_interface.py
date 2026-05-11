"""
Vision Classifier — ros_interface.py

Translates ComputeResult outputs into ROS 2 commands for the
magician_vision_classifier node.

The primary command sets the Vision Model Name / model_path parameter
in the Configuration Module so the classifier loads the new model on reload.
"""

from typing import List
from app.models.use_case import ROS2Command

_NODE = "/magician_vision_classifier"
_CONFIG_NODE = "/magician_configuration"


def get_commands(outputs: dict) -> List[ROS2Command]:
    commands: List[ROS2Command] = []

    model_path = str(outputs.get("model_path", "")).strip()
    if model_path:
        # Set on the classifier node directly
        commands.append(ROS2Command(
            type="param",
            node=_NODE,
            param_name="model_path",
            value=model_path,
        ))
        # Also update the Configuration Module's Vision Model Name parameter
        commands.append(ROS2Command(
            type="param",
            node=_CONFIG_NODE,
            param_name="vision_model_name",
            value=model_path,
        ))

    commands.append(ROS2Command(
        type="param",
        node=_NODE,
        param_name="material_list",
        value=str(outputs.get("materials", "unspecified")),
    ))

    # Trigger model reload
    commands.append(ROS2Command(
        type="service",
        service="/magician_vision_classifier/reload_model",
        service_type="std_srvs/srv/Trigger",
        request_args={},
    ))

    return commands
