"""
Localiser — compute.py

Resolves the /localisation broadcaster's runtime configuration per
COT_LOCALISER.md: a named `setup` republishes its previously registered
calibration transform as static TF, or as slider-corrected dynamic TF.

Mesh is only needed to *register* a new setup (operator picks CAD/TCP point
pairs) — it is never required to broadcast an already-registered setup.
Since COT cannot read the live calibration database, `q_local_setup_registered`
is how the questionnaire tells us which case applies.

Usage (called by compute_runner.py as a subprocess):
    python -m modules.localiser.compute <use_case_json_path> <output_dir>
"""

import json
import os
import sys
from datetime import datetime

from modules.localiser.generate_config import write_config

_DEFAULT_ROBOT_BASE_LINK = "base_link"
_DEFAULT_ROBOT_EE_LINK = "tcp"
_DEFAULT_MESH_LINK = "fender"
_DEFAULT_DATABASE_FILE = "calibration_data.yaml"
_DEFAULT_SLIDER_TOPIC = "/slider/position_y"
_DEFAULT_SLIDER_BIAS = 0.0
_DEFAULT_PUBLISH_RATE_HZ = 30.0


def run(answers: dict) -> dict:
    outputs: dict = {}

    outputs["setup"] = str(answers.get("q_local_setup") or "").strip()
    outputs["setup_missing"] = int(not outputs["setup"])

    setup_registered = answers.get("q_local_setup_registered", "no") == "yes"
    outputs["setup_registered"] = int(setup_registered)

    mesh_path = str(answers.get("q_local_mesh_path") or "").strip()
    outputs["mesh_path"] = mesh_path

    # Mesh is only a blocker when a *new* setup needs registering and none was given.
    outputs["mesh_required"] = int(not setup_registered and not mesh_path)

    outputs["database_file"] = str(answers.get("q_local_database_file") or _DEFAULT_DATABASE_FILE)
    outputs["robot_base_link"] = str(answers.get("q_local_robot_base_link") or _DEFAULT_ROBOT_BASE_LINK)
    outputs["robot_ee_link"] = str(answers.get("q_local_robot_ee_link") or _DEFAULT_ROBOT_EE_LINK)
    outputs["mesh_link"] = str(answers.get("q_local_mesh_link") or _DEFAULT_MESH_LINK)

    motion_mode = answers.get("q_local_motion_mode") or "static"
    outputs["motion_mode"] = motion_mode if motion_mode in ("static", "dynamic") else "static"

    # Static and dynamic broadcasting are mutually exclusive — slider params only apply to dynamic.
    if outputs["motion_mode"] == "dynamic":
        outputs["slider_topic"] = str(answers.get("q_local_slider_topic") or _DEFAULT_SLIDER_TOPIC)
        outputs["slider_bias"] = float(answers.get("q_local_slider_bias") or _DEFAULT_SLIDER_BIAS)
        outputs["publish_rate_hz"] = float(answers.get("q_local_publish_rate_hz") or _DEFAULT_PUBLISH_RATE_HZ)

    return outputs


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage: python -m modules.localiser.compute <use_case_json> <output_dir>",
            file=sys.stderr,
        )
        sys.exit(1)

    use_case_path = sys.argv[1]
    output_dir = sys.argv[2]

    with open(use_case_path, encoding="utf-8") as f:
        use_case = json.load(f)

    answers = use_case.get("answers", {})
    answers = {**answers, **use_case.get("module_answers", {}).get("localiser", {})}

    print(f"[localiser] Computing configuration for use case: {use_case.get('name', '?')}")
    outputs = run(answers)

    os.makedirs(output_dir, exist_ok=True)

    config_path = write_config(outputs, output_dir)
    print(f"[localiser] Params YAML written to {config_path}")

    outputs["params_yaml_path"] = config_path

    result = {
        "module_id": "localiser",
        "success": True,
        "outputs": outputs,
        "error": None,
        "computed_at": datetime.utcnow().isoformat(),
        "artifacts": {
            "params_yaml": config_path,
        },
    }

    out_path = os.path.join(output_dir, "result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"[localiser] Result written to {out_path}")
    for k, v in outputs.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
