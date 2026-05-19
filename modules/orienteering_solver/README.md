# Module: Orienteering Solver

**ROS 2 node:** `/op_solver`  
**Action type:** Reconfiguration (no retraining required)

## What this module does

The Orienteering Solver module selects the correct Orienteering Problem (OP)
variant and configures the solver parameters based on the use case requirements
(number of robot arms, time constraints, custom profit functions). It fires
`ros2 param set` commands to the running `/op_solver` node and triggers a config
reload service call.

## File overview

| File | Purpose |
|---|---|
| `compute.py` | Reads questionnaire answers → selects OP variant + solver params → writes `result.json` |
| `ros_interface.py` | Translates `result.json` outputs into `ROS2Command` objects |
| `README.md` | This file |

## Inputs (from questionnaire)

| Question key | Description |
|---|---|
| `q1_robot_arms` | `"single"` or `"multiple"` |
| `q1_num_arms` | Number of arms (int, only when multiple) |
| `q9_time` | `"none"` or `"tight"` |
| `q9_time_value` | Numeric time budget (when `q9_time == "tight"`) |
| `q9_time_unit` | `"seconds"`, `"minutes"`, or `"hours"` |
| `q10_profit` | `"standard"` or `"custom"` |

## OP variant selection logic

| Condition | Variant |
|---|---|
| Multi-arm + tight time | `OPTW_TOP` |
| Multi-arm, no tight time | `TOP` |
| Single arm, no time limit | `TSP` |
| Single arm, tight time | `OPTW` |
| Custom profit function | `OPVP` |
| Default | `OP` |

## Outputs (written to `result.json`)

| Key | Type | Description |
|---|---|---|
| `op_variant` | `str` | Selected OP variant name |
| `num_agents` | `int` | Number of robot agents |
| `time_budget_seconds` | `float` | Time budget in seconds; `-1` = no limit |
| `custom_profit_enabled` | `int` (0/1) | Whether custom profit function is active |

## ROS 2 commands fired

All commands are `ros2 param set` on `/op_solver`:
- `op_variant`, `num_agents`, `time_budget_seconds`, `custom_profit_enabled`

Followed by a `/op_solver/reload_config` service call.

## How to contribute

1. **Edit `compute.py`** — modify `run(answers)` to extend variant selection or add new solver parameters. Return a flat `dict` of `str | int | float`.
2. **Edit `ros_interface.py`** — add `ROS2Command` entries for any new output keys.
3. Test by running:
   ```
   python -m modules.orienteering_solver.compute <path/to/use_case.json> <output_dir>
   ```
4. Check the generated `result.json`.

> All values passed to ROS 2 must be `str`, `int`, or `float`.
