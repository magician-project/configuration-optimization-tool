"""
Localiser — compute.py

Resolves the localization approach (1, 2, or 3) based on mesh availability
and material type, then writes result.json. The output includes the mesh file
path (if provided) and the selected approach index for the localisation node.

Usage (called by compute_runner.py as a subprocess):
    python -m modules.localiser.compute <use_case_json_path> <output_dir>
"""

import json
import os
import sys
from datetime import datetime


def run(answers: dict) -> dict:
    outputs: dict = {}

    mesh_status = answers.get("q7_mesh")  # "available" | "in_preparation" | "not_available"
    time_constraint = answers.get("q9_time")  # "none" | "tight"

    # Select localisation approach
    if mesh_status == "available":
        outputs["localisation_approach"] = 2   # model-based (approach 2 or 3 — default to 2)
        outputs["mesh_required"] = 1
    else:
        outputs["localisation_approach"] = 1   # model-free
        outputs["mesh_required"] = 0

    # Mesh file path — operator must fill this in before running if mesh is available
    # The placeholder value signals that a real path must be provided.
    outputs["mesh_file_path"] = ""

    # Relaxed pipeline flag
    outputs["relaxed_pipeline"] = 1 if time_constraint == "none" else 0

    # Material list (informs localiser of surface type for approach selection)
    materials = answers.get("q5_materials") or []
    outputs["material_list"] = ",".join(materials) if materials else "unspecified"

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

    print(f"[localiser] Computing configuration for use case: {use_case.get('name', '?')}")
    outputs = run(answers)

    result = {
        "module_id": "localiser",
        "success": True,
        "outputs": outputs,
        "error": None,
        "computed_at": datetime.utcnow().isoformat(),
    }

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"[localiser] Result written to {out_path}")
    for k, v in outputs.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
