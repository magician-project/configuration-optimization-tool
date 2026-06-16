"""
Vision Classifier — ros_interface.py

Translates ComputeResult outputs into ROS 2 commands for the
magician_vision_classifier node.

Runtime-tunable settings (fps, step, threshold, majority voting, two-stage,
model reload) are applied via service calls.  Startup-only settings (laser
topics, laser pixel positions, stream name) are written to live_config.json
by compute.py — those are referenced here as notes until the upstream node
promotes them to proper ROS 2 parameters.
"""

from typing import List
from app.models.use_case import ROS2Command

_NODE = "/magician_vision_classifier"
_CONFIG_NODE = "/magician_configuration"

# Service names from liveClassifierTorchROS.py create_service() calls
_SVC_SET_FPS = "magician_vision_classifier/set_fps"
_SVC_SET_STEP = "magician_vision_classifier/set_step"
_SVC_SET_THRESHOLD = "magician_vision_classifier/set_threshold"
_SVC_SET_MAJ_VOTE = "magician_vision_classifier/set_majority_voting"
_SVC_SET_TWO_STAGE = "magician_vision_classifier/set_two_stage"
_SVC_RELOAD_MODEL = "magician_vision_classifier/reload_model"


def get_commands(outputs: dict) -> List[ROS2Command]:
    commands: List[ROS2Command] = []

    # ── Surface live_config.json path as a note ───────────────────────────
    live_config = outputs.get("artifacts", {}).get("live_config", "")
    if live_config:
        commands.append(ROS2Command(
            type="note",
            node=_NODE,
            param_name="live_config_path",
            value=live_config,
        ))

    # ── model_path → param on classifier node + config module ────────────
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
            node=_CONFIG_NODE,
            param_name="vision_model_name",
            value=model_path,
        ))

    # ── materials list (legacy) ───────────────────────────────────────────
    commands.append(ROS2Command(
        type="param",
        node=_NODE,
        param_name="material_list",
        value=str(outputs.get("materials", "unspecified")),
    ))

    # ── Runtime-tunable settings via service calls ────────────────────────

    # Target FPS (0 = unlimited)
    commands.append(ROS2Command(
        type="service",
        service=_SVC_SET_FPS,
        service_type="example_interfaces/srv/SetFloat64",
        request_args={"data": float(outputs.get("target_fps", 23.0))},
    ))

    # Tile step size
    commands.append(ROS2Command(
        type="service",
        service=_SVC_SET_STEP,
        service_type="example_interfaces/srv/SetInt64",
        request_args={"data": int(outputs.get("step_size", 18))},
    ))

    # Confidence threshold
    commands.append(ROS2Command(
        type="service",
        service=_SVC_SET_THRESHOLD,
        service_type="example_interfaces/srv/SetFloat64",
        request_args={"data": float(outputs.get("threshold", 0.6))},
    ))

    # Majority voting
    commands.append(ROS2Command(
        type="service",
        service=_SVC_SET_MAJ_VOTE,
        service_type="std_srvs/srv/SetBool",
        request_args={"data": bool(outputs.get("majority_voting", True))},
    ))

    # Two-stage ensemble
    commands.append(ROS2Command(
        type="service",
        service=_SVC_SET_TWO_STAGE,
        service_type="std_srvs/srv/SetBool",
        request_args={"data": bool(outputs.get("two_stage_enabled", False))},
    ))

    # Reload model (only if a model path was set)
    if model_path:
        commands.append(ROS2Command(
            type="service",
            service=_SVC_RELOAD_MODEL,
            service_type="std_srvs/srv/Trigger",
            request_args={},
        ))

    return commands
