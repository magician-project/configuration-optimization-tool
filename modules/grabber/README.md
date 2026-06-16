# Module: Grabber

**ROS 2 node:** `/magician_grabber`  
**Action type:** Reconfiguration (no retraining required)

## What this module does

The Grabber module configures the physical manipulation end-effector of MAGICIAN.
Based on the questionnaire answers it determines the correct number of arms,
camera type, extra sensor configuration, and lighting settings, then fires the
corresponding `ros2 param set` commands to the running node.

## File overview

| File | Purpose |
|---|---|
| `compute.py` | Reads questionnaire answers → derives parameter values → writes `result.json` |
| `ros_interface.py` | Translates `result.json` outputs into `ROS2Command` objects |
| `README.md` | This file |

## Inputs (from questionnaire)

These fields remain in the **global questionnaire** (`QuestionnaireAnswers`) because they
influence multiple modules:

| Question key | Description |
|---|---|
| `q1_robot_arms` | `"single"` or `"multiple"` |
| `q1_num_arms` | Number of arms (int, only when multiple) |
| `q2_camera_type` | Camera driver variant (`"standard"`, `"gige"`, `"other"`) |
| `q2_camera_spec` | Optional camera model string |
| `q2_camera_resolution` | `{"width": int, "height": int}` |
| `q2_camera_framerate` | Target frame rate in Hz |
| `q2_stream_shm` | `"yes"` / `"no"` — publish frames to shared memory |
| `q2_stream_shm_name` | POSIX SHM stream name (default `"stream1"`) |
| `q3_additional_sensors` | `["tactile"]`, `["distance"]`, or both |
| `q4_lighting` | `"sufficient"` or `"additional"` |

## Module-specific hardware configuration (Grabber Config tab)

These fields live in `module_answers["grabber"]` (`q_grab_*`), rendered in the
**Module Configuration** tab of the Grabber detail panel:

| Field | CLI flag | Description |
|---|---|---|
| `q_grab_exposure` | `--exposure` | Camera exposure time in µs (capped at 50 000) |
| `q_grab_gain` | `--gain` | Analogue gain |
| `q_grab_blacklevel` | `--blacklevel` | Black-level offset |
| `q_grab_arduino_path` | `--arduino` | Arduino serial port (default `/dev/ttyUSB0`) |
| `q_grab_lighting_mode` | `--rlight/--dlight/--tlight/--trigger` | LED ring control mode |
| `q_grab_teensy_path` | `--teensy` | Teensy serial port (default `/dev/ttyACM0`) |
| `q_grab_force_sensor_ip` | `--atiip` | ATI NetFT IP address |
| `q_grab_force_sensor_port` | `--atiport` | ATI NetFT UDP port (default 49152) |
| `q_grab_tactile_stream` | `--tactilestream` | Tactile SHM stream name (default `"stream_tactile"`) |
| `q_grab_run_duration` | `--duration` | Max capture seconds (0 = run forever) |
| `q_grab_countdown` | `--countdown` | Seconds to count down before starting |
| `q_grab_compress` | `--compress` | Save frames as PNG instead of PNM |
| `q_grab_silent` | `--silent` | Suppress per-frame progress output |
| `q_grab_unixtime` | `--unixtime` | Use Unix epoch timestamps |

## Outputs (written to `result.json`)

| Key | Type | Description |
|---|---|---|
| `multi_arm_mode` | `int` (0/1) | Whether multi-arm mode is active |
| `num_arms` | `int` | Number of active arms |
| `camera_type` | `str` | Camera driver string |
| `camera_spec` | `str` | Optional camera model identifier |
| `extra_sensor_mask` | `int` | Bitmask: tactile=1, vision=2 |
| `extra_lighting` | `int` (0/1) | Extra lighting channels enabled |

## ROS 2 commands fired

All commands are `ros2 param set` on `/magician_grabber`:
- `multi_arm_mode`, `num_arms`, `camera_type`, `camera_spec`, `extra_sensor_mask`, `extra_lighting`

Followed by a `/magician_grabber/reload_config` service call.

## How to contribute

1. **Edit `compute.py`** — add or modify the logic in `run(answers)` that derives parameter values from questionnaire answers. The function must return a flat `dict` of `str | int | float` values.
2. **Edit `ros_interface.py`** — if you add new output keys, add the corresponding `ROS2Command` entries in `get_commands(outputs)`.
3. Test by running:
   ```
   python -m modules.grabber.compute <path/to/use_case.json> <output_dir>
   ```
4. Check the generated `result.json` in `<output_dir>`.

> All values passed to ROS 2 must be `str`, `int`, or `float`. No lists or dicts.
