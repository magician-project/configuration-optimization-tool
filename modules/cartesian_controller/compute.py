"""
Cartesian Controller — compute.py

Resolves the startup configuration of the Cartesian Controller of the IIT grinding runtime:
phase durations, distances and unload settings, with the spec defaults for anything not
answered. `control_rate_hz` is shared with the Impedance Controller, which reads it from here.

Usage (called by compute_runner.py as a subprocess):
    python -m modules.cartesian_controller.compute <use_case_json_path> <output_dir>
"""

import json
import os
import sys
from datetime import datetime

from app.engine.module_config import number_values
from app.engine.schema import CARTESIAN_CONTROLLER_CONFIG

# Always set, never a question: the only unload behaviour COT configures.
_UNLOAD_MODE = "smooth retract"

_STARTUP_NOTE = (
    "startup configuration: the grinding runtime must be restarted for changes to take effect; "
    "COT does not tune it live"
)
_TIME_NOTE = (
    "COT does not check whether the phase durations fit the time constraint of the use case; "
    "contact and safety requirements always take precedence"
)


def run(answers: dict) -> dict:
    """Flat str/float outputs: every answer, or its spec default when unanswered."""
    outputs: dict = number_values(CARTESIAN_CONTROLLER_CONFIG, answers)
    outputs["unload_mode"] = _UNLOAD_MODE
    return outputs


def deploy_blockers(answers: dict) -> list:
    """Every parameter has a spec default, so nothing can be left incomplete."""
    return []


def notes(answers: dict) -> list:
    """Things to know before deploying that do not block it."""
    return [_STARTUP_NOTE, _TIME_NOTE]


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python -m modules.cartesian_controller.compute <use_case_json> <output_dir>", file=sys.stderr)
        sys.exit(1)

    use_case_path = sys.argv[1]
    output_dir = sys.argv[2]

    with open(use_case_path, encoding="utf-8") as f:
        use_case = json.load(f)

    answers = {
        **use_case.get("answers", {}),
        **use_case.get("module_answers", {}).get("cartesian_controller", {}),
    }

    print(f"[cartesian_controller] Computing configuration for use case: {use_case.get('name', '?')}")
    outputs = run(answers)

    result = {
        "module_id": "cartesian_controller",
        "success": True,
        "outputs": outputs,
        "error": None,
        "computed_at": datetime.utcnow().isoformat(),
        "deploy_blockers": deploy_blockers(answers),
        "notes": notes(answers),
    }

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"[cartesian_controller] Result written to {out_path}")
    for k, v in outputs.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
