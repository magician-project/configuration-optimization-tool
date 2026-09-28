# Module: Localiser

**ROS 2 node:** `/localisation`
**Action type:** Reconfiguration (no retraining required)

## What this module does

The Localiser publishes the pose of a workpiece mesh relative to the robot
base, per the partner's `COT_LOCALISER.md` spec. A named **Setup** stores a
calibration transform produced by a manual **Registration** procedure
(operator + robot; not automatable by COT). At runtime the `/localisation`
node either republishes that transform unchanged as static TF, or adds a
live slider displacement and publishes dynamic TF. Static and dynamic modes
are mutually exclusive. See [`CONTEXT.md`](../../CONTEXT.md) for these terms.

COT's job is **not** to perform Registration — it selects and generates the
runtime parameter file the broadcaster loads at startup, and flags when a
new Setup still needs to be registered.

## File overview

| File | Purpose |
|---|---|
| `compute.py` | Reads questionnaire answers → resolves runtime params + blocking conditions → writes `result.json` |
| `generate_config.py` | Writes `localiser_params.yaml`, the ROS 2 parameter file the node reads at startup |
| `ros_interface.py` | Translates `result.json` outputs into `ROS2Command` objects (mostly operator-facing notes) |
| `README.md` | This file |

## Inputs (`module_answers["localiser"]`)

| Question key | Default | Description |
|---|---|---|
| `q_local_setup` | `""` | Name of the calibration `setup` this use case targets (free text; COT cannot validate it exists) |
| `q_local_setup_registered` | `"no"` | `"yes"` if this `setup` was already registered previously; `"no"` means Registration (and therefore a mesh) is still needed |
| `q_local_mesh_path` | `""` | CAD mesh (`.stl`) used by the Registration UI; only required when `q_local_setup_registered == "no"` |
| `q_local_database_file` | package default `calibration_data.yaml` | Broadcaster read path (see caveat below) |
| `q_local_robot_base_link` | `"base_link"` | Parent/output TF frame |
| `q_local_robot_ee_link` | `"tcp"` | TCP frame sampled during Registration |
| `q_local_mesh_link` | `"fender"` | Child TF frame / workpiece identifier |
| `q_local_motion_mode` | `"static"` | `"static"` or `"dynamic"` |
| `q_local_slider_topic` | `"/slider/position_y"` | Dynamic-mode only |
| `q_local_slider_bias` | `0.0` | Dynamic-mode only |
| `q_local_publish_rate_hz` | `30.0` | Dynamic-mode only |

## Mesh requirement logic

Mesh is only needed to **register a new Setup** (pick CAD/TCP point pairs);
an already-registered Setup broadcasts from its stored transform and never
needs the mesh again:

| `q_local_setup_registered` | `q_local_mesh_path` | Result |
|---|---|---|
| `"yes"` | any | Not blocking — mesh is irrelevant, existing Setup is reused |
| `"no"` / empty | provided | Not blocking — mesh is available for Registration |
| `"no"` / empty | `""` | **Blocking** (`mesh_required=1`) — Registration cannot proceed without a mesh |

## Outputs (written to `result.json`)

| Key | Type | Description |
|---|---|---|
| `setup` | `str` | Target calibration setup name |
| `setup_missing` | `int` (0/1) | Blocking flag — `1` when `setup` is blank/whitespace-only |
| `setup_registered` | `int` (0/1) | Whether this setup was already registered |
| `mesh_path` | `str` | CAD mesh path, if provided |
| `mesh_required` | `int` (0/1) | Blocking flag — see table above |
| `database_file` | `str` | Configured calibration database path |
| `robot_base_link`, `robot_ee_link`, `mesh_link` | `str` | TF frame names |
| `motion_mode` | `str` | `"static"` or `"dynamic"` |
| `slider_topic`, `slider_bias`, `publish_rate_hz` | `str`/`float` | Present only when `motion_mode == "dynamic"` |
| `params_yaml_path` | `str` | Path to the generated `localiser_params.yaml` file |

## ROS 2 commands fired

The node has no registration service/action and reads its parameters at
startup, so `ros_interface.py` emits `note` commands rather than live
`ros2 param set` calls:
- `params_yaml_path` — where the generated `localiser_params.yaml` was written
- `setup_missing` — only when `setup_missing == 1` (no setup name provided); fires
  regardless of `setup_registered`
- `setup_registration_reminder` — only when `setup_registered != "yes"`
- `mesh_required` — only when blocking (see table above)
- `database_file_caveat` — always; the current registrator implementation
  ignores the configured `database_file` and always writes to the package
  default, so this reminds the operator the value may not take effect yet

## How to contribute

1. **Edit `compute.py`** — modify `run(answers)` to refine defaults or
   blocking logic. Return a flat `dict` of `str | int | float`.
2. **Edit `generate_config.py`** — add new keys to `localiser_params.yaml`
   as the node's real parameter set grows.
3. **Edit `ros_interface.py`** — add `ROS2Command` entries for new output
   keys; once the partner ships a real reload service/action, replace the
   relevant `note` with a `service` command.
4. Test by running:
   ```
   python -m modules.localiser.compute <path/to/use_case.json> <output_dir>
   ```
   or run the smoke tests:
   ```
   pytest modules/localiser/test_compute.py
   ```

> All values passed to ROS 2 must be `str`, `int`, or `float`.
