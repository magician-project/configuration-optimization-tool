"""
Vision Classifier — generate_config.py

Helpers that turn the flat outputs dict (produced by compute.py) into the
two deployment artifacts consumed by the magician_vision_classifier stack:

  • training_config.json  — bigmodel.json-compatible training configuration
                            passed to trainMagicianVisionClassifierTorch.py
  • live_config.json      — runtime parameters for liveClassifierTorchROS.py
                            (loaded at startup; services are used for runtime tuning)
"""

import json


# ─────────────────────────────────────────────────────────────────────────────
# Training config
# ─────────────────────────────────────────────────────────────────────────────

def generate_training_config(outputs: dict) -> dict:
    """
    Build a dict that matches the schema expected by load_hyperparameters()
    in trainMagicianVisionClassifierTorch.py (the bigmodel.json layout).
    """
    tile_size     = int(outputs.get("tile_size", 48))
    batch_size    = int(outputs.get("batch_size", 64))
    epochs        = int(outputs.get("training_epochs", 10))
    dropout_rate  = float(outputs.get("dropout_rate", 0.25))
    seed          = int(outputs.get("seed", 42))
    grad_clip     = float(outputs.get("gradient_clip_value", 1.0))
    base_channels = int(outputs.get("base_channels", 48))
    dense_layer   = int(outputs.get("final_dense_layer", 512))
    lr            = float(outputs.get("learning_rate", 5e-4))
    val_split     = float(outputs.get("validation_split", 0.2))
    num_workers   = int(outputs.get("num_workers", 0))
    balanced      = bool(outputs.get("balanced_sampling", False))
    cache_ram     = bool(outputs.get("cache_all_to_ram", False))
    loss          = str(outputs.get("loss", "focal"))
    class_weight  = bool(outputs.get("class_weight", False))
    pen_false_clean = float(outputs.get("penalize_false_clean", 0.0))
    dataset_dir   = str(outputs.get("dataset_directory", ""))
    val_dataset   = outputs.get("validation_dataset") or None
    selected_cls  = outputs.get("selected_classes") or []
    accelerator   = str(outputs.get("accelerator", "auto"))
    devices       = int(outputs.get("devices", 1))
    model         = str(outputs.get("model", "resnet18"))
    aolp          = bool(outputs.get("aolp", False))
    dolp          = bool(outputs.get("dolp", False))
    unpolarized   = bool(outputs.get("unpolarized", False))

    # Optional model name prefix (used to build output filenames)
    name = outputs.get("model_name") or "magician"

    config = {
        "name": name,
        "model": model,
        "hparams": {
            "tile_size": tile_size,
            "batch_size": batch_size,
            "training_epochs": epochs,
            "dropout_rate": dropout_rate,
            "seed": seed,
            "gradient_clip_value": grad_clip,
            "base_channels": base_channels,
            "final_dense_layer": dense_layer,
            "AoLP": aolp,
            "DoLP": dolp,
            "unpolarized": unpolarized,
        },
        "optimizer": {
            "type": "AdamW",
            "learning_rate": lr,
        },
        "dataloader": {
            "validation_split": val_split,
            "num_workers": num_workers,
            "balanced_sampling": balanced,
            "cacheAllDataToRAM": cache_ram,
        },
        "loss": loss,
        "penalize_false_clean": pen_false_clean,
        "class_weight": class_weight,
        "accelerator": accelerator,
        "devices": devices,
        "dataset": dataset_dir,
        "selected_classes": selected_cls,
        "wandb": {
            "use_wandb": False,
            "project": "magician",
            "name": name,
        },
    }

    if val_dataset:
        config["validation_dataset"] = val_dataset

    return config


# ─────────────────────────────────────────────────────────────────────────────
# Live inference config
# ─────────────────────────────────────────────────────────────────────────────

def generate_live_config(outputs: dict) -> dict:
    """
    Build a dict for liveClassifierTorchROS.py runtime parameters.

    Currently the classifier reads file-level constants (LASER_TOPICS, etc.),
    so this JSON acts as a bridge until those are promoted to ROS 2 params.
    Runtime-tunable settings (fps, step, threshold, etc.) are applied via
    ROS 2 service calls in ros_interface.py.
    """
    use_lasers = bool(outputs.get("use_lasers", True))

    laser_topics = [
        str(outputs.get("laser_topic_1", "magician_grabber/distance1")),
        str(outputs.get("laser_topic_2", "magician_grabber/distance2")),
        str(outputs.get("laser_topic_3", "magician_grabber/distance3")),
    ]

    laser_xy_pixels = [
        [float(outputs.get("laser_px1_x", 120.0)), float(outputs.get("laser_px1_y", 200.0))],
        [float(outputs.get("laser_px2_x", 320.0)), float(outputs.get("laser_px2_y", 200.0))],
        [float(outputs.get("laser_px3_x", 520.0)), float(outputs.get("laser_px3_y", 200.0))],
    ]

    return {
        "target_fps":        float(outputs.get("target_fps", 23.0)),
        "step_size":         int(outputs.get("step_size", 18)),
        "threshold":         float(outputs.get("threshold", 0.6)),
        "majority_voting":   bool(outputs.get("majority_voting", True)),
        "two_stage_enabled": bool(outputs.get("two_stage_enabled", False)),
        "model_path":        str(outputs.get("model_path", "")),
        "stream_name":       str(outputs.get("stream_name", "stream1")),
        "use_lasers":        use_lasers,
        "laser_topics":      laser_topics,
        "laser_xy_pixels":   laser_xy_pixels,
        "laser_idw_power":   float(outputs.get("laser_idw_power", 2.0)),
    }


def write_configs(outputs: dict, output_dir: str) -> tuple[str, str]:
    """
    Write training_config.json and live_config.json to output_dir.
    Returns (training_config_path, live_config_path).
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    training_path = os.path.join(output_dir, "training_config.json")
    live_path     = os.path.join(output_dir, "live_config.json")

    training_cfg = generate_training_config(outputs)
    live_cfg     = generate_live_config(outputs)

    with open(training_path, "w", encoding="utf-8") as f:
        json.dump(training_cfg, f, indent=2)

    with open(live_path, "w", encoding="utf-8") as f:
        json.dump(live_cfg, f, indent=2)

    return training_path, live_path
