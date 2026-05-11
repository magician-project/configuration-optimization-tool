"""
Orienteering Solver — ros_interface.py

Translates ComputeResult outputs into ROS 2 commands for the op_solver node.
"""

from typing import List
from app.models.use_case import ROS2Command

_NODE = "/op_solver"


def get_commands(outputs: dict) -> List[ROS2Command]:
    commands: List[ROS2Command] = []

    commands.append(ROS2Command(
        type="param",
        node=_NODE,
        param_name="op_variant",
        value=str(outputs.get("op_variant", "OP")),
    ))
    commands.append(ROS2Command(
        type="param",
        node=_NODE,
        param_name="num_agents",
        value=int(outputs.get("num_agents", 1)),
    ))
    commands.append(ROS2Command(
        type="param",
        node=_NODE,
        param_name="time_budget_seconds",
        value=float(outputs.get("time_budget_seconds", -1.0)),
    ))
    commands.append(ROS2Command(
        type="param",
        node=_NODE,
        param_name="custom_profit_enabled",
        value=int(outputs.get("custom_profit_enabled", 0)),
    ))
    commands.append(ROS2Command(
        type="param",
        node=_NODE,
        param_name="material_list",
        value=str(outputs.get("material_list", "unspecified")),
    ))
    commands.append(ROS2Command(
        type="param",
        node=_NODE,
        param_name="defect_types",
        value=str(outputs.get("defect_types", "unspecified")),
    ))

    # After param updates, trigger solver reload via service call
    commands.append(ROS2Command(
        type="service",
        service="/op_solver/reload_config",
        service_type="std_srvs/srv/Trigger",
        request_args={},
    ))

    return commands
