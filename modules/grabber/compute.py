"""
Grabber — compute.py

Entry point for the Grabber computation step. Reads the use case answers and
determines the ROS 2 parameter values needed to configure the Grabber for the
current use case (camera type, number of arms, lighting, extra sensors).

No heavy computation is required for the Grabber — it is purely a reconfiguration
module. This script resolves the correct values and writes result.json so that
ros_interface.py can translate them into ros2 param set / service call commands.

Usage (called by compute_runner.py as a subprocess):
    python -m modules.grabber.compute <use_case_json_path> <output_dir>
"""

import json
import os
import sys
from datetime import datetime


def run(answers: dict) -> dict:
    """
    Derive Grabber configuration from questionnaire answers.
    Returns a flat dict of str/int/float outputs.
    """
    outputs: dict = {}

    # Number of arms → multi-arm mode toggle
    if answers.get("q1_robot_arms") == "multiple":
        outputs["multi_arm_mode"] = 1
        outputs["num_arms"] = int(answers.get("q1_num_arms") or 2)
    else:
        outputs["multi_arm_mode"] = 0
        outputs["num_arms"] = 1

    # Camera type → camera driver selection flag
    cam = answers.get("q2_camera_type", "standard")
    outputs["camera_type"] = cam if cam else "standard"
    if answers.get("q2_camera_spec"):
        outputs["camera_spec"] = str(answers["q2_camera_spec"])

    # Additional sensors → sensor bitmask (tactile=1, vision=2)
    sensor_mask = 0
    sensors = answers.get("q3_additional_sensors") or []
    if "tactile" in sensors:
        sensor_mask |= 1
    if "vision" in sensors:
        sensor_mask |= 2
    outputs["extra_sensor_mask"] = sensor_mask

    # Lighting → extra lighting channels enabled
    outputs["extra_lighting"] = 1 if answers.get("q4_lighting") == "additional" else 0

    return outputs


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python -m modules.grabber.compute <use_case_json> <output_dir>", file=sys.stderr)
        sys.exit(1)

    use_case_path = sys.argv[1]
    output_dir = sys.argv[2]

    with open(use_case_path, encoding="utf-8") as f:
        use_case = json.load(f)

    answers = use_case.get("answers", {})

    print(f"[grabber] Computing configuration for use case: {use_case.get('name', '?')}")
    outputs = run(answers)

    result = {
        "module_id": "grabber",
        "success": True,
        "outputs": outputs,
        "error": None,
        "computed_at": datetime.utcnow().isoformat(),
    }

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"[grabber] Result written to {out_path}")
    for k, v in outputs.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
