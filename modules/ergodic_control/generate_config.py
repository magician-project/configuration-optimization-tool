"""
Ergodic Control — generate_config.py

Writes runtime configuration files for trajectory planning.
"""

import json
import os


def write_configs(outputs: dict, output_dir: str) -> tuple:
    """
    Write trajectory_config.json and kalman_config.json.

    Returns:
        (trajectory_config_path, kalman_config_path)
    """

    # ── Trajectory Configuration ─────────────────────────────────────────────
    trajectory_config = {
        "mesh_path": outputs.get("mesh_path", ""),
        "mesh_available": outputs.get("mesh_available", "no"),
        "sensor_offset_m": outputs.get("sensor_offset_m", 0.05),
        "time_budget_seconds": outputs.get("time_budget_seconds", 60.0),
        "trajectory_density": outputs.get("trajectory_density", "normal"),
        "estimated_trajectory_points": outputs.get("estimated_trajectory_points", 30),
        "camera_framerate_hz": outputs.get("camera_framerate_hz", 30.0),
        "use_historical_data": outputs.get("use_historical_data", True),
        "use_welding_priors": outputs.get("use_welding_priors", True),
        "pdf_grid_resolution": outputs.get("pdf_grid_resolution", 32),
        "stream_name": outputs.get("stream_name", "stream1"),
    }

    trajectory_path = os.path.join(output_dir, "trajectory_config.json")
    with open(trajectory_path, "w", encoding="utf-8") as f:
        json.dump(trajectory_config, f, indent=2)

    # ── Kalman Filter Configuration ──────────────────────────────────────────
    kalman_config = {
        "process_noise_sigma_sq": outputs.get("kalman_process_noise", 0.1),
        "measurement_noise_sigma_sq": outputs.get("kalman_measurement_noise", 0.5),
        "initial_state_variance": 1.0,  # Starting uncertainty about defect distribution
        "update_frequency_hz": outputs.get("camera_framerate_hz", 30.0),
        "filter_type": "extended_kalman_filter",  # EKF for non-linear observation model
        "state_dimension": 2,  # 2D mesh coordinates
        "measurement_dimension": 4,  # (x, y, width, height) from detection
    }

    kalman_path = os.path.join(output_dir, "kalman_config.json")
    with open(kalman_path, "w", encoding="utf-8") as f:
        json.dump(kalman_config, f, indent=2)

    return trajectory_path, kalman_path
