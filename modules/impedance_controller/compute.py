"""
Impedance Controller — compute.py

Resolves the startup configuration of the Impedance Controller of the IIT grinding runtime:
gains, limits and thresholds, with the spec defaults for anything not answered.
`control_rate_hz` is shared: it is owned by the Cartesian Controller and read from there.
The measured wrench topic and source are handled by the required-capabilities work (ticket 12).

Usage (called by compute_runner.py as a subprocess):
    python -m modules.impedance_controller.compute <use_case_json_path> <output_dir>
"""

import json
import os
import sys
from datetime import datetime

from app.engine.module_config import control_rate_blockers, drop_invalid_control_rate, number_values
from app.engine.schema import IMPEDANCE_CONTROLLER_CONFIG
from app.engine.shared_parameters import answers_with_shared

_STARTUP_NOTE = (
    "startup configuration: the grinding runtime must be restarted for changes to take effect; "
    "COT does not tune it live"
)
_RECIPE_NOTE = (
    "COT cannot verify the gains and force limits against the material and tool: "
    "use a validated material-tool recipe and do not infer gains from the material category"
)


def run(answers: dict) -> dict:
    """Flat str/int/float outputs: every answer, or its spec default when unanswered.

    An invalid control rate is left out (and blocks deployment) instead of being written.
    """
    outputs: dict = drop_invalid_control_rate(number_values(IMPEDANCE_CONTROLLER_CONFIG, answers))
    # Unanswered means off until IIT confirms the default.
    outputs["force_sync_enabled"] = answers.get("force_sync_enabled", "no") == "yes"
    return outputs


def deploy_blockers(answers: dict) -> list:
    """Human-readable reasons this configuration must not be deployed yet."""
    return control_rate_blockers(IMPEDANCE_CONTROLLER_CONFIG, answers)


def notes(answers: dict) -> list:
    """Things to know before deploying that do not block it."""
    return [_STARTUP_NOTE, _RECIPE_NOTE]


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python -m modules.impedance_controller.compute <use_case_json> <output_dir>", file=sys.stderr)
        sys.exit(1)

    use_case_path = sys.argv[1]
    output_dir = sys.argv[2]

    with open(use_case_path, encoding="utf-8") as f:
        use_case = json.load(f)

    answers = {
        **use_case.get("answers", {}),
        **answers_with_shared("impedance_controller", use_case.get("module_answers", {})),
    }

    print(f"[impedance_controller] Computing configuration for use case: {use_case.get('name', '?')}")
    outputs = run(answers)

    result = {
        "module_id": "impedance_controller",
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

    print(f"[impedance_controller] Result written to {out_path}")
    for k, v in outputs.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
