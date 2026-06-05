"""
Grabber — compute.py

Entry point for the Grabber computation step. Reads the use case answers and
determines the ROS 2 parameter values needed to configure magician_grabber.

Writes three files to output_dir:
  • result.json       — COT standard result envelope
  • params.yaml       — ROS 2 parameter YAML (pass via --params-file at launch)
  • launch_args.txt   — equivalent CLI argument string for direct invocation

Usage (called by compute_runner.py as a subprocess):
    python -m modules.grabber.compute <use_case_json_path> <output_dir>
"""

import json
import os
import sys
from datetime import datetime

from modules.grabber.generate_config import generate_yaml, generate_launch_args


def run(answers: dict) -> dict:
    """
    Derive Grabber configuration from questionnaire answers.
    Returns a flat dict of str/int/float/bool outputs.
    """
    outputs: dict = {}

    # ── Robot arms ──────────────────────────────────────────────────────────
    if answers.get("q1_robot_arms") == "multiple":
        outputs["multi_arm_mode"] = 1
        outputs["num_arms"] = int(answers.get("q1_num_arms") or 2)
    else:
        outputs["multi_arm_mode"] = 0
        outputs["num_arms"] = 1

    # ── Camera ──────────────────────────────────────────────────────────────
    cam = answers.get("q2_camera_type", "standard")
    outputs["camera_type"] = cam if cam else "standard"
    if answers.get("q2_camera_spec"):
        outputs["camera_spec"] = str(answers["q2_camera_spec"])

    outputs["use_camera"] = cam != "none"

    # Camera resolution
    cam_res = answers.get("q2_camera_resolution") or {}
    if cam_res.get("width"):
        outputs["width"]  = int(cam_res["width"])
    if cam_res.get("height"):
        outputs["height"] = int(cam_res["height"])

    if answers.get("q2_camera_framerate"):
        fps = float(answers["q2_camera_framerate"])
        outputs["frame_rate"] = fps
        # >10 Hz requires RAM-backed storage
        outputs["use_ram"] = fps > 10.0
    else:
        outputs["use_ram"] = False

    if answers.get("q2_camera_exposure"):
        outputs["exposure"] = int(answers["q2_camera_exposure"])

    if answers.get("q2_camera_gain") is not None:
        outputs["gain"] = float(answers["q2_camera_gain"])

    if answers.get("q2_camera_blacklevel") is not None:
        outputs["black_level"] = float(answers["q2_camera_blacklevel"])

    # Shared memory streaming
    outputs["stream_data"] = answers.get("q2_stream_shm") == "yes"
    outputs["camera_stream_name"] = (
        str(answers["q2_stream_shm_name"])
        if answers.get("q2_stream_shm_name")
        else "stream1"
    )

    # ── Additional sensors ───────────────────────────────────────────────────
    sensors = answers.get("q3_additional_sensors") or []
    outputs["use_ati_force"] = "tactile" in sensors
    outputs["use_teensy"]    = "tactile" in sensors
    outputs["use_arduino"]   = "distance" in sensors or "tactile" in sensors

    # Keep legacy bitmask for backwards compatibility
    sensor_mask = 0
    if "tactile"  in sensors: sensor_mask |= 1
    if "vision"   in sensors: sensor_mask |= 2
    if "distance" in sensors: sensor_mask |= 4
    outputs["extra_sensor_mask"] = sensor_mask

    # Serial paths
    if answers.get("q3_arduino_path"):
        outputs["arduino_path"] = str(answers["q3_arduino_path"])
    if answers.get("q3_teensy_path"):
        outputs["teensy_path"] = str(answers["q3_teensy_path"])

    # Tactile stream name
    outputs["tactile_stream_name"] = (
        str(answers["q3_tactile_stream"])
        if answers.get("q3_tactile_stream")
        else "stream_tactile"
    )

    # ATI force sensor
    if answers.get("q3_force_sensor_ip"):
        outputs["ati_ip"] = str(answers["q3_force_sensor_ip"])
    if answers.get("q3_force_sensor_port"):
        outputs["ati_port"] = int(answers["q3_force_sensor_port"])

    # ── Lighting ─────────────────────────────────────────────────────────────
    outputs["extra_lighting"] = 1 if answers.get("q4_lighting") == "additional" else 0

    lighting = answers.get("q3_lighting_mode", "none")
    outputs["lighting_mode"]        = lighting if lighting else "none"
    outputs["manual_trigger_light"] = lighting == "trigger"

    # ── Run-time / misc ───────────────────────────────────────────────────────
    outputs["run_forever"] = True
    outputs["compress"]    = False
    outputs["simulate"]    = False

    return outputs


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python -m modules.grabber.compute <use_case_json> <output_dir>", file=sys.stderr)
        sys.exit(1)

    use_case_path = sys.argv[1]
    output_dir    = sys.argv[2]

    with open(use_case_path, encoding="utf-8") as f:
        use_case = json.load(f)

    answers = use_case.get("answers", {})

    print(f"[grabber] Computing configuration for use case: {use_case.get('name', '?')}")
    outputs = run(answers)

    os.makedirs(output_dir, exist_ok=True)

    # Write params.yaml
    yaml_str = generate_yaml(outputs)
    yaml_path = os.path.join(output_dir, "params.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_str)
    print(f"[grabber] ROS 2 params YAML written to {yaml_path}")

    # Write launch_args.txt
    launch_str = generate_launch_args(outputs)
    args_path = os.path.join(output_dir, "launch_args.txt")
    with open(args_path, "w", encoding="utf-8") as f:
        f.write(launch_str + "\n")
    print(f"[grabber] Launch args written to {args_path}")

    result = {
        "module_id": "grabber",
        "success": True,
        "outputs": outputs,
        "error": None,
        "computed_at": datetime.utcnow().isoformat(),
        "artifacts": {
            "params_yaml": yaml_path,
            "launch_args": args_path,
        },
    }

    out_path = os.path.join(output_dir, "result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"[grabber] Result written to {out_path}")
    for k, v in outputs.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
