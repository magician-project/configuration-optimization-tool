# Module: Vision Classifier

**ROS 2 node:** `/magician_vision_classifier`, `/magician_configuration`  
**Action type:** Retrain + Reconfiguration

## What this module does

The Vision Classifier module determines whether the vision model needs to be
retrained for the new use case (different materials or surface types) and, once
trained, passes the path of the new model file to the ROS 2 nodes so they can
load it.

## File overview

| File | Purpose |
|---|---|
| `compute.py` | Checks if retraining is needed → calls `train.py` → writes `result.json` |
| `ros_interface.py` | Translates `result.json` outputs into `ROS2Command` objects |
| `train.py` | **Training entry point** — implement this to run the actual vision model training |
| `README.md` | This file |

## Inputs (from questionnaire)

| Question key | Description |
|---|---|
| `q5_materials` | List of material types the camera will inspect |

## Outputs (written to `result.json`)

| Key | Type | Description |
|---|---|---|
| `materials` | `str` | Comma-separated list of materials |
| `retrain_required` | `int` (0/1) | Whether retraining was triggered |
| `model_path` | `str` | Absolute path to the trained model file |

## ROS 2 commands fired

`ros2 param set` on `/magician_vision_classifier`:
- `model_path`

`ros2 param set` on `/magician_configuration`:
- `vision_model_name` (set to the basename of `model_path`)

Followed by a `/magician_vision_classifier/reload_model` service call.

## How to implement training

The `train.py` file contains a placeholder `run_training()` function that raises
`NotImplementedError`. To implement it:

1. Open `train.py` and implement `run_training(materials, output_dir)`.
2. The function must:
   - Train (or fine-tune) the vision model on data for the given materials.
   - Save the model file to `output_dir`.
   - Return the absolute path to the saved model file as a `str`.
3. `compute.py` will call `run_training()` automatically when retraining is required
   and will write the returned path to `result.json` as `model_path`.

```python
# train.py skeleton
def run_training(materials: list, output_dir: str) -> str:
    """
    Train the vision classifier model.
    Returns the path to the saved model file.
    """
    # Your training code here
    ...
    return str(model_path)
```

## How to contribute

1. Implement `train.py` as described above.
2. Optionally extend `compute.py` to pass additional parameters (e.g. defect types)
   to `run_training()`.
3. Test by running:
   ```
   python -m modules.vision_classifier.compute <path/to/use_case.json> <output_dir>
   ```
4. Verify `result.json` contains a valid `model_path`.

> All values passed to ROS 2 must be `str`, `int`, or `float`.
