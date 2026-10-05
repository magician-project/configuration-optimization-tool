"""
Motion Planner — generate_config.py

Writes motion_planner_params.yaml, the ROS 2 parameter file for
--ros-args --params-file, from the section-4 settings compute.py resolves.
"""

import os

import yaml


def write_config(outputs: dict, output_dir: str) -> str:
    """
    Write motion_planner_params.yaml. Returns its path.
    """
    params: dict = {
        "base_link": outputs.get("base_link", "base_link"),
        "ee_link": outputs.get("ee_link", "tcp"),
        "integration_dt": float(outputs.get("integration_dt", 0.001)),
        "ft_link": outputs.get("ft_link", outputs.get("ee_link", "tcp")),
        "proportional_gain": float(outputs.get("proportional_gain", 1 / 3600)),
        "integral_gain": float(outputs.get("integral_gain", 4.6)),
        "integral_bound": float(outputs.get("integral_bound", 0.02)),
        "integral_velocity_bound": float(outputs.get("integral_velocity_bound", 0.01)),
        "mini58_topic": outputs.get("mini58_topic", "/ati_ft_sensor/wrench_sensed"),
        "nano17_topic": outputs.get("nano17_topic", "/magician_grabber/wrench_sensed"),
        "impedance_sensor": outputs.get("impedance_sensor", "force_estimate"),
        "debug_prints": bool(outputs.get("debug_prints", False)),
        "debug_lib": bool(outputs.get("debug_lib", False)),
    }

    doc = {"motion_planner": {"ros__parameters": params}}

    params_path = os.path.join(output_dir, "motion_planner_params.yaml")
    with open(params_path, "w", encoding="utf-8") as f:
        yaml.dump(doc, f, default_flow_style=False, sort_keys=False)

    return params_path
