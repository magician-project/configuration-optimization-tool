"""
Vision Classifier — compute.py

Runs the vision classifier retraining pipeline.
The key output sent to ROS 2 is the path to the newly trained model file so
the Configuration Module can load it via the Vision Model Name parameter.

Usage (called by compute_runner.py as a subprocess):
    python -m modules.vision_classifier.compute <use_case_json_path> <output_dir>
"""

import json
import os
import sys
from datetime import datetime


def run(answers: dict, output_dir: str) -> dict:
    outputs: dict = {}

    materials = answers.get("q5_materials") or []
    outputs["materials"] = ",".join(materials) if materials else "unspecified"

    needs_retrain = bool(materials)
    outputs["retrain_required"] = 1 if needs_retrain else 0

    if needs_retrain:
        # TODO: call train.py here when the vision training pipeline is ready.
        # Example:
        #   from modules.vision_classifier.train import run_training
        #   model_path = run_training(materials, output_dir)
        #
        # The returned path is passed to the ROS 2 node as the model_path param.
        model_path = os.path.join(output_dir, "vision_model_placeholder.pth")
        outputs["model_path"] = model_path
        print(f"[vision_classifier] Retraining required — model placeholder: {model_path}")
        print("  NOTE: Replace with real training call once training pipeline is ready.")
    else:
        outputs["model_path"] = ""
        print("[vision_classifier] No retraining required for this configuration.")

    return outputs


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage: python -m modules.vision_classifier.compute <use_case_json> <output_dir>",
            file=sys.stderr,
        )
        sys.exit(1)

    use_case_path = sys.argv[1]
    output_dir = sys.argv[2]

    with open(use_case_path, encoding="utf-8") as f:
        use_case = json.load(f)

    answers = use_case.get("answers", {})

    print(f"[vision_classifier] Computing configuration for use case: {use_case.get('name', '?')}")
    outputs = run(answers, output_dir)

    result = {
        "module_id": "vision_classifier",
        "success": True,
        "outputs": outputs,
        "error": None,
        "computed_at": datetime.utcnow().isoformat(),
    }

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"[vision_classifier] Result written to {out_path}")
    for k, v in outputs.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
