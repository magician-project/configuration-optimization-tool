"""
Ergodic Control — ros_interface.py

Translates ComputeResult outputs into ROS 2 commands for the
magician_ergodic_control node and motion planner integration.
"""

from typing import List
from app.models.use_case import ROS2Command

_NODE = "/magician_ergodic_control"
_CONFIG_NODE = "/magician_configuration"
_MOTION_PLANNER_SVC = "/motion_planner/execute_trajectory_on_mesh"

# Service types (example_interfaces for demonstration)
_SVC_SET_FLOAT = "example_interfaces/srv/SetFloat64"
_SVC_SET_INT = "example_interfaces/srv/SetInt64"
_SVC_SET_BOOL = "example_interfaces/srv/SetBool"
_SVC_SET_STRING = "example_interfaces/srv/SetString"


def get_commands(outputs: dict) -> List[ROS2Command]:
    """
    Generate ROS 2 commands to configure ergodic control trajectory planning.
    """
    commands: List[ROS2Command] = []

    # ── Configuration node parameters ────────────────────────────────────
    commands.append(ROS2Command(
        type="param",
        node=_CONFIG_NODE,
        param_name="ergodic_control_enabled",
        value=True,
    ))

    # ── Mesh file path ───────────────────────────────────────────────────
    mesh_path = str(outputs.get("mesh_path", "")).strip()
    if mesh_path:
        commands.append(ROS2Command(
            type="param",
            node=_NODE,
            param_name="mesh_file_path",
            value=mesh_path,
        ))

    # ── Sensor offset (camera standoff) via service call ──────────────
    sensor_offset = float(outputs.get("sensor_offset_m", 0.05))
    commands.append(ROS2Command(
        type="service",
        service=f"{_NODE}/set_sensor_offset",
        service_type=_SVC_SET_FLOAT,
        request_args={"data": sensor_offset},
    ))

    # ── Time budget via service call ─────────────────────────────────
    time_budget = float(outputs.get("time_budget_seconds", 60.0))
    commands.append(ROS2Command(
        type="service",
        service=f"{_NODE}/set_time_budget",
        service_type=_SVC_SET_FLOAT,
        request_args={"data": time_budget},
    ))

    # ── Trajectory density ───────────────────────────────────────────
    trajectory_density = str(outputs.get("trajectory_density", "normal"))
    commands.append(ROS2Command(
        type="service",
        service=f"{_NODE}/set_trajectory_density",
        service_type=_SVC_SET_STRING,
        request_args={"data": trajectory_density},
    ))

    # ── PDF grid resolution via service call ────────────────────────
    pdf_resolution = int(outputs.get("pdf_grid_resolution", 32))
    commands.append(ROS2Command(
        type="service",
        service=f"{_NODE}/set_pdf_resolution",
        service_type=_SVC_SET_INT,
        request_args={"data": pdf_resolution},
    ))

    # ── Historical data flag ────────────────────────────────────────
    use_historical = outputs.get("use_historical_data", True)
    commands.append(ROS2Command(
        type="service",
        service=f"{_NODE}/set_use_historical_data",
        service_type=_SVC_SET_BOOL,
        request_args={"data": use_historical},
    ))

    # ── Welding priors flag ────────────────────────────────────────
    use_welding = outputs.get("use_welding_priors", True)
    commands.append(ROS2Command(
        type="service",
        service=f"{_NODE}/set_use_welding_priors",
        service_type=_SVC_SET_BOOL,
        request_args={"data": use_welding},
    ))

    # ── Kalman filter parameters via service calls ─────────────────
    process_noise = float(outputs.get("kalman_process_noise", 0.1))
    commands.append(ROS2Command(
        type="service",
        service=f"{_NODE}/set_process_noise",
        service_type=_SVC_SET_FLOAT,
        request_args={"data": process_noise},
    ))

    measurement_noise = float(outputs.get("kalman_measurement_noise", 0.5))
    commands.append(ROS2Command(
        type="service",
        service=f"{_NODE}/set_measurement_noise",
        service_type=_SVC_SET_FLOAT,
        request_args={"data": measurement_noise},
    ))

    # ── Note with config file paths ──────────────────────────────────
    trajectory_config = outputs.get("artifacts", {}).get("trajectory_config", "")
    kalman_config = outputs.get("artifacts", {}).get("kalman_config", "")

    if trajectory_config:
        commands.append(ROS2Command(
            type="note",
            node=_NODE,
            param_name="trajectory_config_path",
            value=trajectory_config,
        ))

    if kalman_config:
        commands.append(ROS2Command(
            type="note",
            node=_NODE,
            param_name="kalman_config_path",
            value=kalman_config,
        ))

    # ── Material and defect information ────────────────────────────────
    materials = str(outputs.get("target_materials", "unspecified"))
    commands.append(ROS2Command(
        type="param",
        node=_NODE,
        param_name="target_materials",
        value=materials,
    ))

    defects = str(outputs.get("defect_types", "unspecified"))
    commands.append(ROS2Command(
        type="param",
        node=_NODE,
        param_name="defect_types",
        value=defects,
    ))

    # ── Stream name for shared memory camera data ──────────────────────
    stream_name = str(outputs.get("stream_name", "stream1"))
    commands.append(ROS2Command(
        type="param",
        node=_NODE,
        param_name="camera_stream_name",
        value=stream_name,
    ))

    return commands
