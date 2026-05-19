# Module: Tactile Sensor (Tactile Classifier)

**ROS 2 node:** `/tactile_classifier_system`  
**Action type:** Retrain + Reconfiguration

## What this module does

The Tactile Sensor module determines whether the CNN-LSTM tactile classifier
needs to be retrained for the new use case (different materials, defect types,
or object sizes) and, once trained, passes the path of the new model checkpoint
to the ROS 2 node.

## File overview

| File | Purpose |
|---|---|
| `compute.py` | Checks if retraining is needed → calls `train.py` → writes `result.json` |
| `ros_interface.py` | Translates `result.json` outputs into `ROS2Command` objects |
| `train.py` | **Training entry point** — implement this to run the actual CNN-LSTM training |
| `README.md` | This file |

## Inputs (from questionnaire)

| Question key | Description |
|---|---|
| `q5_materials` | List of material types the sensor will encounter |
| `q6_object_size` | Object size category (affects training data selection) |
| `q8_defects` | List of defect types to detect |

## Outputs (written to `result.json`)

| Key | Type | Description |
|---|---|---|
| `materials` | `str` | Comma-separated list of materials |
| `defects` | `str` | Comma-separated list of defect types |
| `object_size` | `str` | Object size category |
| `retrain_required` | `int` (0/1) | Whether retraining was triggered |
| `model_path` | `str` | Absolute path to the trained model checkpoint |

## ROS 2 commands fired

`ros2 param set` on `/tactile_classifier_system`:
- `model_path`

Followed by a `/tactile_classifier_system/reload_model` service call.

## How to implement training

The `train.py` file contains a placeholder `run_training()` function that raises
`NotImplementedError`. To implement it:

1. Open `train.py` and implement `run_training(materials, defects, object_size, output_dir)`.
2. The function must:
   - Train (or fine-tune) the CNN-LSTM model using the provided parameters.
   - Save the model checkpoint to `output_dir`.
   - Return the absolute path to the saved checkpoint file as a `str`.
3. `compute.py` will call `run_training()` automatically when retraining is required
   and will write the returned path to `result.json` as `model_path`.

```python
# train.py skeleton
def run_training(materials: list, defects: list, object_size: str, output_dir: str) -> str:
    """
    Train the tactile classifier model.
    Returns the path to the saved model checkpoint.
    """
    # Your training code here
    ...
    return str(checkpoint_path)
```

## How to contribute

1. Implement `train.py` as described above.
2. Optionally extend `compute.py` to pass additional parameters to `run_training()`.
3. Test by running:
   ```
   python -m modules.tactile_sensor.compute <path/to/use_case.json> <output_dir>
   ```
4. Verify `result.json` contains a valid `model_path`.

> All values passed to ROS 2 must be `str`, `int`, or `float`.
