# Modules

Each subdirectory in this folder corresponds to one MAGICIAN ROS 2 module.
Module owners work exclusively inside their own folder.

## Module overview

| Folder | Module | ROS 2 node | Action type |
|---|---|---|---|
| `grabber/` | Grabber | `/magician_grabber` | Reconfiguration |
| `orienteering_solver/` | Orienteering Solver | `/op_solver` | Reconfiguration |
| `localiser/` | Localiser | `/localisation` | Reconfiguration |
| `tactile_sensor/` | Tactile Sensor | `/tactile_classifier_system` | Retrain + Reconfigure |
| `vision_classifier/` | Vision Classifier | `/magician_vision_classifier` | Retrain + Reconfigure |

## Folder structure (per module)

```
modules/<module_id>/
├── README.md          ← Start here: inputs, outputs, how to contribute
├── __init__.py
├── compute.py         ← Derives parameter values from questionnaire answers
├── ros_interface.py   ← Maps outputs to ros2 param set / service call commands
└── train.py           ← (ML modules only) Training pipeline entry point
```

## How the system uses your module

1. The user fills in the questionnaire in the COT GUI.
2. COT computes which modules are affected and marks them as *Action required*.
3. The user opens a module tile and clicks **Run Compute**.
4. COT spawns your `compute.py` as a subprocess:
   ```
   python -m modules.<module_id>.compute <use_case.json> <output_dir>
   ```
5. `compute.py` writes `result.json` to `<output_dir>`.
6. The user reviews the result and clicks **Deploy to ROS 2**.
7. COT calls `ros_interface.get_commands(outputs)` and fires the resulting
   `ros2 param set` / `ros2 service call` commands on the robot machine.

## Contract for `compute.py`

The `run(answers)` function (or `run(answers, output_dir)` for ML modules) must:
- Accept a `dict` of questionnaire answer key/value pairs.
- Return a **flat** `dict` where every value is `str`, `int`, or `float`.
- Print progress lines to stdout (they appear live in the GUI).
- Exit with code `0` on success, non-zero on failure.

The `main()` function writes the result dict to `<output_dir>/result.json`.

## Contract for `ros_interface.py`

The `get_commands(outputs: dict) -> List[ROS2Command]` function must:
- Accept the flat outputs dict from `result.json`.
- Return an ordered list of `ROS2Command` objects (param sets first, service calls last).
- Only use `str`, `int`, or `float` as command values.

## Testing your module locally

```bash
# From the repo root (with .venv activated)
python -m modules.<module_id>.compute data/use_cases/<id>/use_case.json /tmp/test_out
cat /tmp/test_out/result.json
```

## ROS mock mode

By default the application runs with `ROS_MOCK=true`, so deploy commands are
logged but not actually fired. Set `ROS_MOCK=false` on the robot machine to
enable real ROS 2 command execution.
