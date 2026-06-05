"""
Vision Classifier — compute.py

Reads questionnaire answers and produces:
  • result.json           — COT standard result envelope
  • training_config.json  — bigmodel.json-compatible training config for
                            trainMagicianVisionClassifierTorch.py
  • live_config.json      — runtime parameters for liveClassifierTorchROS.py

Model selection logic:
  1. If q_clf_model_path is provided and the file exists → skip training,
     use the existing checkpoint.
  2. If q_clf_dataset_dir is provided → set retrain_required=1, write
     training_config.json so the operator can run the trainer manually.
  3. Otherwise → warn that no model source is configured.

Usage (called by compute_runner.py as a subprocess):
    python -m modules.vision_classifier.compute <use_case_json_path> <output_dir>
"""

import json
import os
import sys
from datetime import datetime

from modules.vision_classifier.generate_config import write_configs


def run(answers: dict, output_dir: str) -> dict:
    outputs: dict = {}

    # ── Material context (kept for backwards compat) ─────────────────────────
    materials = answers.get("q5_materials") or []
    outputs["materials"] = ",".join(materials) if materials else "unspecified"

    # ── Model backbone ───────────────────────────────────────────────────────
    outputs["model"] = str(answers.get("q_clf_model", "resnet18"))

    # ── Tile / inference geometry ────────────────────────────────────────────
    tile_size = answers.get("q_clf_tile_size", "48")
    outputs["tile_size"] = int(tile_size) if tile_size else 48

    outputs["step_size"]  = int(answers.get("q_clf_step_size", 18) or 18)
    outputs["threshold"]  = float(answers.get("q_clf_threshold", 0.6) or 0.6)
    outputs["target_fps"] = float(answers.get("q_clf_fps", 23.0) or 23.0)

    outputs["majority_voting"]   = answers.get("q_clf_majority_voting", "yes") == "yes"
    outputs["two_stage_enabled"] = answers.get("q_clf_two_stage", "no") == "yes"

    # ── Training hyperparameters ──────────────────────────────────────────────
    outputs["training_epochs"]     = int(answers.get("q_clf_epochs", 10) or 10)
    outputs["batch_size"]          = int(answers.get("q_clf_batch_size", 64) or 64)
    outputs["learning_rate"]       = float(answers.get("q_clf_learning_rate", 5e-4) or 5e-4)
    outputs["loss"]                = str(answers.get("q_clf_loss", "focal") or "focal")
    outputs["dropout_rate"]        = 0.25
    outputs["seed"]                = 42
    outputs["gradient_clip_value"] = 1.0
    outputs["base_channels"]       = 48
    outputs["final_dense_layer"]   = 512
    outputs["validation_split"]    = 0.2
    outputs["num_workers"]         = 0
    outputs["balanced_sampling"]   = False
    outputs["cache_all_to_ram"]    = False
    outputs["class_weight"]        = False
    outputs["penalize_false_clean"]= 0.0
    outputs["accelerator"]         = "auto"
    outputs["devices"]             = 1
    outputs["selected_classes"]    = []

    # ── Polarization channels (advanced) ─────────────────────────────────────
    outputs["aolp"]        = answers.get("q_clf_aolp", "no") == "yes"
    outputs["dolp"]        = answers.get("q_clf_dolp", "no") == "yes"
    outputs["unpolarized"] = answers.get("q_clf_unpolarized", "no") == "yes"

    # ── Dataset / model path ─────────────────────────────────────────────────
    model_path  = str(answers.get("q_clf_model_path", "") or "").strip()
    dataset_dir = str(answers.get("q_clf_dataset_dir", "") or "").strip()

    if model_path and os.path.isfile(model_path):
        outputs["retrain_required"] = 0
        outputs["model_path"] = model_path
        print(f"[vision_classifier] Using existing model checkpoint: {model_path}")
    elif dataset_dir:
        outputs["retrain_required"] = 1
        outputs["dataset_directory"] = dataset_dir
        # Expected model output path after training (stem matches training config name)
        stem = f"{answers.get('q_clf_model', 'resnet18')}_{outputs['tile_size']}px"
        outputs["model_path"] = os.path.join(dataset_dir, f"{stem}.pth")
        outputs["model_name"] = stem
        print(f"[vision_classifier] Retraining required — dataset: {dataset_dir}")
        print(f"  Run:  python trainMagicianVisionClassifierTorch.py training_config.json")
    else:
        outputs["retrain_required"] = 0
        outputs["model_path"] = model_path  # may be empty; warn
        if not model_path:
            print("[vision_classifier] WARNING: No model path or dataset directory provided. "
                  "live_config.json will have an empty model_path.")

    # ── Laser distance fusion ─────────────────────────────────────────────────
    outputs["use_lasers"] = answers.get("q_clf_use_lasers", "yes") == "yes"

    outputs["laser_topic_1"] = str(answers.get("q_clf_laser_topic_1", "magician_grabber/distance1") or "magician_grabber/distance1")
    outputs["laser_topic_2"] = str(answers.get("q_clf_laser_topic_2", "magician_grabber/distance2") or "magician_grabber/distance2")
    outputs["laser_topic_3"] = str(answers.get("q_clf_laser_topic_3", "magician_grabber/distance3") or "magician_grabber/distance3")

    outputs["laser_px1_x"] = float(answers.get("q_clf_laser_px1_x", 120.0) or 120.0)
    outputs["laser_px1_y"] = float(answers.get("q_clf_laser_px1_y", 200.0) or 200.0)
    outputs["laser_px2_x"] = float(answers.get("q_clf_laser_px2_x", 320.0) or 320.0)
    outputs["laser_px2_y"] = float(answers.get("q_clf_laser_px2_y", 200.0) or 200.0)
    outputs["laser_px3_x"] = float(answers.get("q_clf_laser_px3_x", 520.0) or 520.0)
    outputs["laser_px3_y"] = float(answers.get("q_clf_laser_px3_y", 200.0) or 200.0)
    outputs["laser_idw_power"] = float(answers.get("q_clf_laser_idw_power", 2.0) or 2.0)

    # ── Shared memory stream name ─────────────────────────────────────────────
    outputs["stream_name"] = str(answers.get("q2_stream_shm_name", "stream1") or "stream1")

    return outputs


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage: python -m modules.vision_classifier.compute <use_case_json> <output_dir>",
            file=sys.stderr,
        )
        sys.exit(1)

    use_case_path = sys.argv[1]
    output_dir    = sys.argv[2]

    with open(use_case_path, encoding="utf-8") as f:
        use_case = json.load(f)

    answers = use_case.get("answers", {})

    print(f"[vision_classifier] Computing configuration for use case: {use_case.get('name', '?')}")
    outputs = run(answers, output_dir)

    os.makedirs(output_dir, exist_ok=True)

    # Write training_config.json and live_config.json
    training_path, live_path = write_configs(outputs, output_dir)
    print(f"[vision_classifier] Training config written to {training_path}")
    print(f"[vision_classifier] Live config written to    {live_path}")

    result = {
        "module_id": "vision_classifier",
        "success": True,
        "outputs": outputs,
        "error": None,
        "computed_at": datetime.utcnow().isoformat(),
        "artifacts": {
            "training_config": training_path,
            "live_config": live_path,
        },
    }

    out_path = os.path.join(output_dir, "result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"[vision_classifier] Result written to {out_path}")
    for k, v in outputs.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()



if __name__ == "__main__":
    main()
