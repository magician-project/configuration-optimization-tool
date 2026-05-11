"""
Orienteering Solver — compute.py

Resolves the correct OP variant and solver parameters based on the questionnaire
answers, then writes result.json. No external solver is invoked here — the
outputs are the configuration parameters (variant name, flags, time limits) that
will be passed to the running op_solver ROS 2 node via ros_interface.py.

Usage (called by compute_runner.py as a subprocess):
    python -m modules.orienteering_solver.compute <use_case_json_path> <output_dir>
"""

import json
import os
import sys
from datetime import datetime


def run(answers: dict) -> dict:
    """
    Determine OP variant and associated solver configuration.
    Returns a flat dict of str/int/float outputs.
    """
    outputs: dict = {}

    multi_arm = answers.get("q1_robot_arms") == "multiple"
    num_arms = int(answers.get("q1_num_arms") or 2) if multi_arm else 1
    time_constraint = answers.get("q9_time")
    custom_profit = answers.get("q10_profit") == "custom"

    # OP variant selection
    if multi_arm and time_constraint == "tight":
        variant = "OPTW_TOP"   # multi-arm + time windows
    elif multi_arm:
        variant = "TOP"
    elif time_constraint == "none":
        variant = "TSP"
    elif time_constraint == "tight":
        variant = "OPTW"
    elif custom_profit:
        variant = "OPVP"
    else:
        variant = "OP"

    outputs["op_variant"] = variant
    outputs["num_agents"] = num_arms

    # Time budget
    if time_constraint == "tight" and answers.get("q9_time_value") is not None:
        time_value = float(answers["q9_time_value"])
        time_unit = answers.get("q9_time_unit", "minutes")
        # Normalise to seconds for the ROS node
        multipliers = {"seconds": 1.0, "minutes": 60.0, "hours": 3600.0}
        outputs["time_budget_seconds"] = time_value * multipliers.get(time_unit, 60.0)
    else:
        outputs["time_budget_seconds"] = -1.0   # -1 = no limit

    # Custom profit flag
    outputs["custom_profit_enabled"] = 1 if custom_profit else 0

    # Material list (comma-separated string for ROS param)
    materials = answers.get("q5_materials") or []
    if "other" in materials and answers.get("q5_other_material"):
        materials = [m for m in materials if m != "other"] + [answers["q5_other_material"]]
    outputs["material_list"] = ",".join(materials) if materials else "unspecified"

    # Defect types (comma-separated)
    defects = answers.get("q8_defects") or []
    outputs["defect_types"] = ",".join(defects) if defects else "unspecified"

    return outputs


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage: python -m modules.orienteering_solver.compute <use_case_json> <output_dir>",
            file=sys.stderr,
        )
        sys.exit(1)

    use_case_path = sys.argv[1]
    output_dir = sys.argv[2]

    with open(use_case_path, encoding="utf-8") as f:
        use_case = json.load(f)

    answers = use_case.get("answers", {})

    print(f"[orienteering_solver] Computing configuration for use case: {use_case.get('name', '?')}")
    outputs = run(answers)

    result = {
        "module_id": "orienteering_solver",
        "success": True,
        "outputs": outputs,
        "error": None,
        "computed_at": datetime.utcnow().isoformat(),
    }

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"[orienteering_solver] Result written to {out_path}")
    for k, v in outputs.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
