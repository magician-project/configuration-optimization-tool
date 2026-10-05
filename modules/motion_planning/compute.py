"""
Motion Planner — compute.py

Resolves the /motion_planner node's configuration per section 4 of
COT_MOTION_PLANNER.md: reference frames, admittance/impedance control
tuning, force-sensor topics, impedance sensor selection, and debug flags.

Usage (called by compute_runner.py as a subprocess):
    python -m modules.motion_planning.compute <use_case_json_path> <output_dir>
"""

import json
import os
import sys
from datetime import datetime

from modules.motion_planning.generate_config import write_config

_DEFAULT_BASE_LINK = "base_link"
_DEFAULT_EE_LINK = "tcp"
_DEFAULT_INTEGRATION_DT = 0.001
_DEFAULT_PROPORTIONAL_GAIN = 1 / 3600
_DEFAULT_INTEGRAL_GAIN = 4.6
_DEFAULT_INTEGRAL_BOUND = 0.02
_DEFAULT_INTEGRAL_VELOCITY_BOUND = 0.01
_DEFAULT_MINI58_TOPIC = "/ati_ft_sensor/wrench_sensed"
_DEFAULT_NANO17_TOPIC = "/magician_grabber/wrench_sensed"
_DEFAULT_IMPEDANCE_SENSOR = "force_estimate"


def run(answers: dict) -> dict:
    outputs: dict = {}

    # ── Reference frames ─────────────────────────────────────────────────────
    base_link = str(answers.get("q_mp_base_link") or _DEFAULT_BASE_LINK)
    ee_link = str(answers.get("q_mp_ee_link") or _DEFAULT_EE_LINK)
    outputs["base_link"] = base_link
    outputs["ee_link"] = ee_link
    # ft_link defaults to ee_link per COT_MOTION_PLANNER.md
    outputs["ft_link"] = str(answers.get("q_mp_ft_link") or ee_link)

    # ── Planner sampling ─────────────────────────────────────────────────────
    outputs["integration_dt"] = float(answers.get("q_mp_integration_dt") or _DEFAULT_INTEGRATION_DT)
    # An external/legacy params file may still name this `integration_timestep`;
    # COT always surfaces a caveat (see ros_interface.py) about that risk.
    outputs["integration_dt_rename_pending"] = True

    # ── Z-admittance control tuning ──────────────────────────────────────────
    outputs["proportional_gain"] = float(answers.get("q_mp_proportional_gain") or _DEFAULT_PROPORTIONAL_GAIN)
    outputs["integral_gain"] = float(answers.get("q_mp_integral_gain") or _DEFAULT_INTEGRAL_GAIN)
    outputs["integral_bound"] = float(answers.get("q_mp_integral_bound") or _DEFAULT_INTEGRAL_BOUND)
    outputs["integral_velocity_bound"] = float(
        answers.get("q_mp_integral_velocity_bound") or _DEFAULT_INTEGRAL_VELOCITY_BOUND
    )

    # ── Force/torque sensor sources ──────────────────────────────────────────
    outputs["mini58_topic"] = str(answers.get("q_mp_mini58_topic") or _DEFAULT_MINI58_TOPIC)
    outputs["nano17_topic"] = str(answers.get("q_mp_nano17_topic") or _DEFAULT_NANO17_TOPIC)
    impedance_sensor = str(answers.get("q_mp_impedance_sensor") or _DEFAULT_IMPEDANCE_SENSOR)
    outputs["impedance_sensor"] = (
        impedance_sensor if impedance_sensor in ("force_estimate", "mini58", "nano17") else _DEFAULT_IMPEDANCE_SENSOR
    )

    # ── Diagnostics ───────────────────────────────────────────────────────────
    outputs["debug_prints"] = answers.get("q_mp_debug_prints", "no") == "yes"
    outputs["debug_lib"] = answers.get("q_mp_debug_lib", "no") == "yes"

    return outputs


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage: python -m modules.motion_planning.compute <use_case_json> <output_dir>",
            file=sys.stderr,
        )
        sys.exit(1)

    use_case_path = sys.argv[1]
    output_dir = sys.argv[2]

    with open(use_case_path, encoding="utf-8") as f:
        use_case = json.load(f)

    answers = use_case.get("answers", {})
    answers = {**answers, **use_case.get("module_answers", {}).get("motion_planning", {})}

    print(f"[motion_planning] Computing configuration for use case: {use_case.get('name', '?')}")
    outputs = run(answers)

    os.makedirs(output_dir, exist_ok=True)

    params_path = write_config(outputs, output_dir)
    print(f"[motion_planning] Params YAML written to {params_path}")

    result = {
        "module_id": "motion_planning",
        "success": True,
        "outputs": outputs,
        "error": None,
        "computed_at": datetime.utcnow().isoformat(),
        "artifacts": {
            "params_yaml": params_path,
        },
    }

    out_path = os.path.join(output_dir, "result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"[motion_planning] Result written to {out_path}")
    for k, v in outputs.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
