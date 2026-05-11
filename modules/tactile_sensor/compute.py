"""
Tactile Sensor (Tactile Classifier) — compute.py

Runs the tactile classifier retraining pipeline.
In production this calls train.py which trains the CNN-LSTM model on new
material/defect-type data. The key output sent to ROS 2 is the path to the
newly trained model checkpoint.

Usage (called by compute_runner.py as a subprocess):
    python -m modules.tactile_sensor.compute <use_case_json_path> <output_dir>
"""

import json
import os
import sys
from datetime import datetime


def run(answers: dict, output_dir: str) -> dict:
    """
    Determine whether retraining is needed and (when implemented) invoke it.
    Returns a dict of str/int/float outputs including the new model path.
    """
    outputs: dict = {}

    materials = answers.get("q5_materials") or []
    defects = answers.get("q8_defects") or []
    object_size = answers.get("q6_object_size") or "unknown"

    outputs["materials"] = ",".join(materials) if materials else "unspecified"
    outputs["defect_types"] = ",".join(defects) if defects else "unspecified"
    outputs["object_size"] = object_size

    needs_retrain = bool(materials or defects)
    outputs["retrain_required"] = 1 if needs_retrain else 0

    if needs_retrain:
        # TODO: call train.py here when training data and pipeline are ready.
        # Example:
        #   from modules.tactile_sensor.train import run_training
        #   model_path = run_training(materials, defects, object_size, output_dir)
        #
        # For now we emit a placeholder path so the rest of the pipeline can proceed.
        model_path = os.path.join(output_dir, "tactile_model_placeholder.pth")
        outputs["model_path"] = model_path
        print(f"[tactile_sensor] Retraining required — model placeholder: {model_path}")
        print("  NOTE: Replace with real training call once training pipeline is ready.")
    else:
        outputs["model_path"] = ""
        print("[tactile_sensor] No retraining required for this configuration.")

    return outputs


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage: python -m modules.tactile_sensor.compute <use_case_json> <output_dir>",
            file=sys.stderr,
        )
        sys.exit(1)

    use_case_path = sys.argv[1]
    output_dir = sys.argv[2]

    with open(use_case_path, encoding="utf-8") as f:
        use_case = json.load(f)

    answers = use_case.get("answers", {})

    print(f"[tactile_sensor] Computing configuration for use case: {use_case.get('name', '?')}")
    outputs = run(answers, output_dir)

    result = {
        "module_id": "tactile_sensor",
        "success": True,
        "outputs": outputs,
        "error": None,
        "computed_at": datetime.utcnow().isoformat(),
    }

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"[tactile_sensor] Result written to {out_path}")
    for k, v in outputs.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
