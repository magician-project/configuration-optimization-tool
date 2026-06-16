"""
Ergodic Control — compute.py

Reads questionnaire answers and produces:
  • result.json           — COT standard result envelope
  • trajectory_config.json  — parameters for ergodic trajectory planning
  • kalman_config.json    — Kalman filter parameters for live node

Model selection logic:
  1. Check if mesh file is available
  2. Determine if historical data exists from previous use case
  3. Check if welding process data can be used
  4. Set Kalman filter parameters based on sensor configuration
  5. Configure trajectory density based on time budget

Usage (called by compute_runner.py as a subprocess):
    python -m modules.ergodic_control.compute <use_case_json_path> <output_dir>
"""

import json
import os
import sys
from datetime import datetime

from modules.ergodic_control.generate_config import write_configs


def run(answers: dict, output_dir: str) -> dict:
    outputs: dict = {}

    # ── Mesh configuration ───────────────────────────────────────────────────
    mesh_available = answers.get("q_ergodic_mesh_available", "yes")
    mesh_path = str(answers.get("q_ergodic_mesh_path", "")).strip()

    outputs["mesh_available"] = mesh_available
    outputs["mesh_path"] = mesh_path if mesh_available == "available" or mesh_available == "yes" else ""

    if mesh_available != "yes" and mesh_available != "available":
        print("[ergodic_control] WARNING: Mesh not available. Trajectory planning may be limited.")

    # ── Time budget & trajectory density ─────────────────────────────────────
    time_budget = float(answers.get("q_ergodic_time_budget", 60.0) or 60.0)
    outputs["time_budget_seconds"] = time_budget

    trajectory_density = str(answers.get("q_ergodic_trajectory_density", "normal") or "normal")
    outputs["trajectory_density"] = trajectory_density  # "sparse" | "normal" | "dense"

    # Estimate trajectory points based on time budget and density
    # Assume: 30 points/min for normal density
    base_points = int((time_budget / 60.0) * 30)
    density_multipliers = {"sparse": 0.5, "normal": 1.0, "dense": 1.5}
    outputs["estimated_trajectory_points"] = max(
        10, int(base_points * density_multipliers.get(trajectory_density, 1.0))
    )

    # ── Sensor offset (camera standoff distance) ─────────────────────────────
    sensor_offset = float(answers.get("q_ergodic_sensor_offset", 0.05) or 0.05)
    outputs["sensor_offset_m"] = sensor_offset
    print(f"[ergodic_control] Camera standoff distance: {sensor_offset} m")

    # ── Historical data usage ───────────────────────────────────────────────
    use_historical = answers.get("q_ergodic_use_historical", "yes") == "yes"
    outputs["use_historical_data"] = use_historical
    outputs["historical_data_required"] = use_historical  # Flag for data validation

    # ── Welding process priors ──────────────────────────────────────────────
    use_welding = answers.get("q_ergodic_use_welding_priors", "yes") == "yes"
    outputs["use_welding_priors"] = use_welding
    print(f"[ergodic_control] Using welding process priors: {'yes' if use_welding else 'no'}")

    # ── Kalman Filter parameters ────────────────────────────────────────────
    # Process noise: higher = more trust in motion model, lower = less trust
    process_noise = float(answers.get("q_ergodic_kalman_process_noise", 0.1) or 0.1)
    outputs["kalman_process_noise"] = process_noise

    # Measurement noise: higher = less trust in measurements, lower = more trust
    measurement_noise = float(answers.get("q_ergodic_kalman_measurement_noise", 0.5) or 0.5)
    outputs["kalman_measurement_noise"] = measurement_noise

    # ── PDF computation resolution ──────────────────────────────────────────
    pdf_resolution = int(answers.get("q_ergodic_pdf_resolution", 32) or 32)
    outputs["pdf_grid_resolution"] = pdf_resolution  # 16, 32, 64, or 128
    print(f"[ergodic_control] PDF grid resolution: {pdf_resolution}x{pdf_resolution}")

    # ── Defect information from materials ────────────────────────────────────
    materials = answers.get("q5_materials") or []
    defects = answers.get("q8_defects") or []
    outputs["target_materials"] = ",".join(materials) if materials else "unspecified"
    outputs["defect_types"] = ",".join(defects) if defects else "unspecified"

    # ── Camera and vision classifier integration ────────────────────────────
    camera_type = str(answers.get("q2_camera_type", "standard") or "standard")
    camera_framerate = float(answers.get("q2_camera_framerate", 30.0) or 30.0)
    outputs["camera_type"] = camera_type
    outputs["camera_framerate_hz"] = camera_framerate

    # ── ROS topic names ────────────────────────────────────────────────────
    stream_name = str(answers.get("q2_stream_shm_name", "stream1") or "stream1")
    outputs["stream_name"] = stream_name
    outputs["ros_node_name"] = "/magician_ergodic_control"
    outputs["motion_planner_service"] = "/motion_planner/execute_trajectory_on_mesh"

    return outputs


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage: python -m modules.ergodic_control.compute <use_case_json> <output_dir>",
            file=sys.stderr,
        )
        sys.exit(1)

    use_case_path = sys.argv[1]
    output_dir = sys.argv[2]

    with open(use_case_path, encoding="utf-8") as f:
        use_case = json.load(f)

    answers = use_case.get("answers", {})
    # Merge in module-specific answers (q_ergodic_* fields stored separately)
    answers = {**answers, **use_case.get("module_answers", {}).get("ergodic_control", {})}

    print(f"[ergodic_control] Computing configuration for use case: {use_case.get('name', '?')}")
    outputs = run(answers, output_dir)

    os.makedirs(output_dir, exist_ok=True)

    # Write trajectory_config.json and kalman_config.json
    trajectory_path, kalman_path = write_configs(outputs, output_dir)
    print(f"[ergodic_control] Trajectory config written to {trajectory_path}")
    print(f"[ergodic_control] Kalman config written to    {kalman_path}")

    result = {
        "module_id": "ergodic_control",
        "success": True,
        "outputs": outputs,
        "error": None,
        "computed_at": datetime.utcnow().isoformat(),
        "artifacts": {
            "trajectory_config": trajectory_path,
            "kalman_config": kalman_path,
        },
    }

    out_path = os.path.join(output_dir, "result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"[ergodic_control] Result written to {out_path}")
    for k, v in outputs.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
