# Module: Localiser

**ROS 2 node:** `/localisation`  
**Action type:** Reconfiguration (no retraining required)

## What this module does

The Localiser module selects the correct localisation approach (model-free vs
model-based) depending on whether a 3D mesh of the inspection target is
available, and configures the `/localisation` ROS 2 node accordingly.

## File overview

| File | Purpose |
|---|---|
| `compute.py` | Reads questionnaire answers → selects approach + mesh path → writes `result.json` |
| `ros_interface.py` | Translates `result.json` outputs into `ROS2Command` objects |
| `README.md` | This file |

## Inputs (from questionnaire)

| Question key | Description |
|---|---|
| `q5_materials` | List of material types (used for surface type hints) |
| `q7_mesh` | `"available"`, `"in_preparation"`, or `"not_available"` |
| `q9_time` | `"none"` or `"tight"` (determines relaxed pipeline flag) |

## Localisation approach selection

| `q7_mesh` value | Approach | Description |
|---|---|---|
| `"available"` | `2` | Model-based localisation |
| `"in_preparation"` or `"not_available"` | `1` | Model-free localisation |

## Outputs (written to `result.json`)

| Key | Type | Description |
|---|---|---|
| `localisation_approach` | `int` (1 or 2) | Selected approach index |
| `mesh_required` | `int` (0/1) | Whether a mesh file is needed |
| `mesh_file_path` | `str` | Path to the mesh file (must be filled by operator before deploy when `mesh_required=1`) |
| `relaxed_pipeline` | `int` (0/1) | Use relaxed (faster) pipeline when there is no time constraint |
| `material_hints` | `str` | Comma-separated material list for surface type selection |

## ROS 2 commands fired

All commands are `ros2 param set` on `/localisation`:
- `localisation_approach`, `mesh_file_path`, `relaxed_pipeline`, `material_hints`

Followed by a `/localisation/reload_config` service call.

## How to contribute

1. **Edit `compute.py`** — modify `run(answers)` to refine approach selection
   (e.g. distinguish approach 2 vs approach 3 when mesh quality is known).
   Return a flat `dict` of `str | int | float`.
2. **Mesh file path** — the `mesh_file_path` output is intentionally left empty
   (`""`). The operator must provide the actual path before clicking Deploy.
   Future work: add a file-picker in the module detail dialog.
3. **Edit `ros_interface.py`** — add `ROS2Command` entries for new output keys.
4. Test by running:
   ```
   python -m modules.localiser.compute <path/to/use_case.json> <output_dir>
   ```

> All values passed to ROS 2 must be `str`, `int`, or `float`.
