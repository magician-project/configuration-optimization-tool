# Magician Grabber & Vision Classifier — COT Integration Plan

**Status:** Planning  
**Scope:** `modules/grabber`, `modules/vision_classifier`, `app/engine/schema.py` and supporting layers  
**Out of scope:** `magician_grabber_annotator` (standalone GUI, no COT integration)

---

## 1. Overview

The MAGICIAN hardware stack consists of three tightly coupled repositories:

| Repository | Role |
|---|---|
| `magician_grabber` | C++ ROS 2 node — polarization camera acquisition, ATI force/torque, accelerometer (Teensy), distance/light controller (Arduino) |
| `magician_vision_classifier` | Python — CNN training (`trainMagicianVisionClassifierTorch.py`) and live inference ROS 2 node (`liveClassifierTorchROS.py`) |
| `magician_grabber_annotator` | wxPython annotation GUI (out of scope) |

Currently the COT has placeholder implementations for both modules. This plan replaces those placeholders with real parameter handling, correct output artifacts, and appropriate ROS 2 integration for each component.

---

## 2. Parameter Inventory

### 2.1 Grabber parameters

Source files: `common.h` (L317 region — `GlobalConfig` struct) and `ros_magician_grabber.cpp` (L165 region — node constructor and `parse_arguments`).

| Parameter | Type | Default | Source flag / struct field | Notes |
|---|---|---|---|---|
| `useCamera` | bool | 0 | `--camera` / `cfg.useCamera` | GigE camera thread |
| `useArduino` | bool | 0 | `--distance` / `cfg.useArduino` | Distance sensor + lighting controller |
| `useTeensy` | bool | 0 | `--accelerometer` / `cfg.useTeensy` | Accelerometer via Teensy |
| `useATIForce` | bool | 0 | `--force` / `cfg.useATIForce` | ATI NetFT force/torque |
| `streamData` | bool | 0 | `--stream` / `cfg.streamData` | Publish frames to POSIX SHM |
| `width` | uint | camera default | `--size <w> <h>` | Capture width in pixels |
| `height` | uint | camera default | `--size <w> <h>` | Capture height in pixels |
| `exposure` | uint (µs) | camera default | `--exposure` | Max allowed: `MAXIMUM_ALLOWED_EXPOSURE_IN_MICROSECONDS` |
| `gain` | double | camera default | `--gain` | Analogue gain |
| `blackLevel` | double | camera default | `--blacklevel` | Black-level offset |
| `frameRate` | double | camera default | `--fps` | Hz; >10 Hz requires `--ram` |
| `atiIP` | string | "192.168.137.201" | `--atiip` | ATI NetFT IP address |
| `atiPort` | int | 49152 | `--atiport` | ATI NetFT UDP port |
| `arduinoPath` | string | "/dev/ttyUSB0" | `--arduino` | Serial device for Arduino |
| `teensyPath` | string | "/dev/ttyACM0" | `--teensy` | Serial device for Teensy |
| `manual_trigger_light` | bool | 0 | `--trigger` / `--notrigger` | Send light-change after each frame |
| `lightingMode` | enum | none | `--rlight` / `--dlight` / `--tlight` | Round-robin / distance-based / pattern |
| `cameraStreamName` | string | "stream1" | `--camerastream` | POSIX SHM stream name |
| `tactileStreamName` | string | "stream_tactile" | `--tactilestream` | POSIX SHM stream name for tactile |
| `useRAM` | bool | 0 | `--ram` | Write to tmpfs (required at >10 Hz) |
| `compress` | bool | 0 | `--compress` | Save frames as PNG (vs PNM) |
| `run_forever` | bool | 1 | `--forever` / `--duration` | Ignore time limit when 1 |
| `maxTimeToGrabForInSeconds` | ulong | — | `--duration <s>` | Only used when `run_forever=0` |
| `countdown` | uchar | 0 | `--countdown <s>` | Seconds before capture starts |
| `simulate` | bool | 0 | `--simulate` | Simulation mode (no hardware) |

**Startup-only parameters** (cannot be changed at runtime via `ros2 param set`; require a node restart):  
`useCamera`, `useArduino`, `useTeensy`, `useATIForce`, `streamData`, `width`, `height`, `exposure`, `gain`, `blackLevel`, `frameRate`, `atiIP`, `atiPort`, `arduinoPath`, `teensyPath`, `lightingMode`, `cameraStreamName`, `tactileStreamName`, `useRAM`, `compress`, `simulate`

### 2.2 Vision Classifier — training parameters

Source file: `trainMagicianVisionClassifierTorch.py` (L1323 region) and `configs/bigmodel.json`.

| Parameter | Type | Default (bigmodel.json) | JSON path | Notes |
|---|---|---|---|---|
| `model` | string | "resnet18" | `model` | Backbone: resnet18, resnext50, convnext_tiny, efficientnet_v2_s, swin_v2_t, regnet_y_800mf, regnet_y_400mf, mobilenet_v3_small/large, shufflenet_v2_x0_5/x1_0, squeezenet1_1, efficientnet_b0, densenet121, mnasnet0_5/1_0, custom_cnn |
| `tile_size` | int | 48 | `hparams.tile_size` | Must match live inference tile size |
| `batch_size` | int | 64 | `hparams.batch_size` | |
| `training_epochs` | int | 10 | `hparams.training_epochs` | |
| `dropout_rate` | float | 0.25 | `hparams.dropout_rate` | |
| `seed` | int | 42 | `hparams.seed` | Reproducibility |
| `gradient_clip_value` | float | 1.0 | `hparams.gradient_clip_value` | |
| `base_channels` | int | 48 | `hparams.base_channels` | For custom CNN only |
| `final_dense_layer` | int | 512 | `hparams.final_dense_layer` | For custom CNN only |
| `learning_rate` | float | 5e-4 | `optimizer.learning_rate` | AdamW |
| `validation_split` | float | (in JSON) | `dataloader.validation_split` | Fraction for validation |
| `num_workers` | int | 0 (auto) | `dataloader.num_workers` | 0 = auto-detect |
| `balanced_sampling` | bool | false | `dataloader.balanced_sampling` | BalancedBatchSampler |
| `cacheAllDataToRAM` | bool | false | `dataloader.cacheAllDataToRAM` | Pre-load dataset to RAM |
| `loss` | string | "focal" | `loss` | "focal" or "cross_entropy" |
| `class_weight` | bool | false | `class_weight` | Inverse-frequency weighting |
| `penalize_false_clean` | float | 0.0 | `penalize_false_clean` | Extra penalty for false-clean predictions |
| `dataset_directory` | string | — | `dataset` | Path to training data |
| `validation_dataset` | string | null | `validation_dataset` | Optional separate validation set |
| `selected_classes` | list | [] | `selected_classes` | Filter to a subset of classes |
| `accelerator` | string | "auto" | `accelerator` | "auto", "cpu", "gpu" |
| `devices` | int | 1 | `devices` | Number of GPUs/CPUs |
| *(advanced)* `AoLP` | bool | false | `hparams.AoLP` | Add angle-of-linear-polarization channel |
| *(advanced)* `DoLP` | bool | false | `hparams.DoLP` | Add degree-of-linear-polarization channel |
| *(advanced)* `unpolarized` | bool | false | `hparams.unpolarized` | Add intensity (mean of 4 channels) |

### 2.3 Vision Classifier — live inference parameters

Source file: `liveClassifierTorchROS.py` (L330 and L793 regions).

| Parameter | Type | Default | Exposed via | Notes |
|---|---|---|---|---|
| `target_fps` | float | 23.0 | `set_fps` service | 0 = no limiting |
| `step_size` | int | 18 | `set_step` service | Pixel stride between tiles |
| `threshold` | float | 0.6 | `set_threshold` service | Min softmax confidence to register a defect |
| `majority_voting` | bool | true | `set_majority_voting` service | 3×3 spatial smoothing |
| `two_stage_enabled` | bool | false | `set_two_stage` service | Use ensemble classifier |
| `USE_LASERS` | bool | true | File-level constant → COT generates param | Whether to subscribe to laser distance topics |
| `LASER_TOPICS` | list[str] | ["magician_grabber/distance1-3"] | File-level constant → COT generates param | ROS topic names for 3 laser sensors |
| `LASER_XY_PIXELS` | list[tuple] | [(120,200),(320,200),(520,200)] | File-level constant → COT generates param | Pixel positions of lasers in image plane |
| `LASER_IDW_POWER` | float | 2.0 | File-level constant → COT generates param | IDW interpolation power |
| `model_path` | string | — | `set_model` service + `reload_model` trigger | Path to `.pth` file |
| `stream_name` | string | "stream1" | Startup param | POSIX SHM stream to read frames from |

---

## 3. Questionnaire Schema Changes

### 3.1 New questions for Section B (Sensors & Perception)

These questions follow from or extend existing `q2_camera_type` and `q3_additional_sensors` questions.

| Question ID | Title | Type | Drives |
|---|---|---|---|
| `q2_camera_resolution` | Camera resolution | two-number (width × height) | `width`, `height` |
| `q2_camera_framerate` | Target frame rate (Hz) | number (float) | `frameRate`, implies `useRAM` when >10 |
| `q2_camera_exposure` | Exposure time (µs) | number (int) | `exposure` |
| `q2_camera_gain` | Camera gain | number (float) | `gain` |
| `q2_camera_blacklevel` | Black-level offset | number (float) | `blackLevel` |
| `q2_stream_shm` | Stream frames to shared memory | bool/select | `streamData`, `cameraStreamName` |
| `q3_force_sensor_ip` | ATI NetFT IP address | text (follow-up from q3 tactile) | `atiIP` |
| `q3_force_sensor_port` | ATI NetFT UDP port | number (follow-up from q3 tactile) | `atiPort` |
| `q3_arduino_path` | Arduino serial port | text (follow-up from q3 tactile/distance) | `arduinoPath` |
| `q3_teensy_path` | Teensy serial port | text (follow-up from q3 tactile/accel) | `teensyPath` |
| `q3_lighting_mode` | Lighting controller mode | select (round-robin / distance / pattern / manual-trigger) | `lightingMode`, `manual_trigger_light` |
| `q3_tactile_stream` | Tactile stream name | text | `tactileStreamName` |

### 3.2 New questions for Section D (Defect Detection)

| Question ID | Title | Type | Drives |
|---|---|---|---|
| `q_clf_model` | Classifier backbone architecture | select (resnet18, resnext50, convnext_tiny, etc.) | `model` (training + live) |
| `q_clf_tile_size` | Tile size (pixels) | number (int, e.g. 32/48/64) | `tile_size` (training + live) |
| `q_clf_step_size` | Inference tile step | number (int) | `step_size` live |
| `q_clf_threshold` | Detection confidence threshold | number (float 0–1) | `threshold` live |
| `q_clf_fps` | Target inference FPS | number (float) | `target_fps` live |
| `q_clf_majority_voting` | Majority voting | bool/select | `majority_voting` live |
| `q_clf_two_stage` | Enable two-stage ensemble | bool/select | `two_stage_enabled` live |
| `q_clf_model_path` | Path to pre-trained model | text (optional) | `model_path` live; skip training if provided |
| `q_clf_dataset_dir` | Training dataset directory | text (if re-training) | `dataset_directory` training |
| `q_clf_epochs` | Training epochs | number | `training_epochs` training |
| `q_clf_batch_size` | Training batch size | number | `batch_size` training |
| `q_clf_learning_rate` | Learning rate | number (float) | `learning_rate` training |
| `q_clf_loss` | Loss function | select (focal / cross_entropy) | `loss` training |
| `q_clf_use_lasers` | Enable laser distance fusion | bool/select | `USE_LASERS` live |
| `q_clf_laser_topics` | Laser ROS topic names (3) | three text fields | `LASER_TOPICS` live |
| `q_clf_laser_pixels` | Laser pixel positions (3 × x,y) | six number fields | `LASER_XY_PIXELS` live |
| `q_clf_laser_idw_power` | IDW interpolation power | number (float) | `LASER_IDW_POWER` live |

### 3.3 Advanced/optional subsection (polarization channels)

Rendered only when an "Advanced settings" toggle is enabled in the GUI (Section D or new section):

| Question ID | Title | Type | Drives |
|---|---|---|---|
| `q_clf_aolp` | Include AoLP channel | bool | `AoLP` training |
| `q_clf_dolp` | Include DoLP channel | bool | `DoLP` training |
| `q_clf_unpolarized` | Include unpolarized (mean) channel | bool | `unpolarized` training |

### 3.4 New confidence categories

Add to `schema.py` `confidence_categories`:

| ID | Label | Fields |
|---|---|---|
| 8 | Grabber Hardware | `q2_camera_resolution`, `q2_camera_framerate`, `q3_force_sensor_ip`, `q3_lighting_mode` |
| 9 | Classifier Config | `q_clf_model`, `q_clf_tile_size`, `q_clf_threshold`, `q_clf_model_path` |

---

## 4. Output Artifacts

For each use case, the following files are written to `data/use_cases/<id>/compute_outputs/`:

### 4.1 Grabber outputs (`compute_outputs/grabber/`)

| File | Format | Consumer |
|---|---|---|
| `result.json` | COT standard result envelope | GUI (already exists) |
| `params.yaml` | ROS 2 parameter YAML for `ros2 run ... --ros-args --params-file` | Operator at grabber startup |
| `launch_args.txt` | Full CLI string `magician_grabber --camera --fps 15 --atiip 192.168.x.x ...` | Operator / CI pipeline |

**`params.yaml` structure:**
```yaml
magician_grabber:
  ros__parameters:
    use_camera: true
    use_arduino: true
    use_teensy: true
    use_ati_force: true
    stream_data: true
    width: 1224
    height: 1024
    exposure: 5000
    gain: 1.0
    black_level: 0.0
    frame_rate: 15.0
    ati_ip: "192.168.137.201"
    ati_port: 49152
    arduino_path: "/dev/ttyUSB0"
    teensy_path: "/dev/ttyACM0"
    lighting_mode: "rlight"
    camera_stream_name: "stream1"
    tactile_stream_name: "stream_tactile"
    use_ram: true
    compress: false
```

### 4.2 Vision Classifier outputs (`compute_outputs/vision_classifier/`)

| File | Format | Consumer |
|---|---|---|
| `result.json` | COT standard result envelope | GUI (already exists) |
| `training_config.json` | bigmodel.json-compatible training config | `trainMagicianVisionClassifierTorch.py` |
| `live_config.json` | Runtime classifier parameters | `liveClassifierTorchROS.py` startup / service calls |

**`training_config.json` structure** (bigmodel.json schema):
```json
{
  "hparams": {
    "tile_size": 48,
    "batch_size": 64,
    "training_epochs": 10,
    "dropout_rate": 0.25,
    "seed": 42,
    "gradient_clip_value": 1.0,
    "base_channels": 48,
    "final_dense_layer": 512,
    "AoLP": false,
    "DoLP": false,
    "unpolarized": false
  },
  "optimizer": { "type": "AdamW", "learning_rate": 5e-4 },
  "dataloader": {
    "validation_split": 0.2,
    "num_workers": 0,
    "balanced_sampling": false,
    "cacheAllDataToRAM": false
  },
  "loss": "focal",
  "penalize_false_clean": 0.0,
  "class_weight": false,
  "accelerator": "auto",
  "model": "resnet18",
  "devices": 1,
  "dataset": "/path/to/dataset",
  "selected_classes": []
}
```

**`live_config.json` structure:**
```json
{
  "target_fps": 23.0,
  "step_size": 18,
  "threshold": 0.6,
  "majority_voting": true,
  "two_stage_enabled": false,
  "model_path": "./allclass_resnet18.pth",
  "stream_name": "stream1",
  "use_lasers": true,
  "laser_topics": [
    "magician_grabber/distance1",
    "magician_grabber/distance2",
    "magician_grabber/distance3"
  ],
  "laser_xy_pixels": [[120.0, 200.0], [320.0, 200.0], [520.0, 200.0]],
  "laser_idw_power": 2.0
}
```

---

## 5. ROS 2 Integration Strategy

### 5.1 Grabber

The grabber is a **startup-only** C++ node. Settings cannot be changed at runtime via `ros2 param set`. The COT therefore:

1. **Writes `params.yaml`** — operator passes this to the node at launch:
   ```bash
   ros2 run rclcpp_magician_grabber magician_grabber --ros-args --params-file params.yaml
   ```
2. **Writes `launch_args.txt`** — equivalent CLI string using `parse_arguments` flags as documented in `common.h::print_help()`.
3. **No `ros2 param set` commands** are generated for the grabber (they would be silently ignored at runtime). The existing `ros_interface.py` commands are replaced by a "write file" action.

### 5.2 Vision Classifier

The classifier **does** expose runtime services. The COT generates two categories of commands:

**a) Startup (parameter YAML or env file):**
- `model_path`, `stream_name`, `USE_LASERS`, `LASER_TOPICS`, `LASER_XY_PIXELS`, `LASER_IDW_POWER` — these are currently file-level constants in `liveClassifierTorchROS.py`. Until they are refactored to ROS 2 params, the COT writes `live_config.json` and the node can be patched to load it at startup.

**b) Runtime (service calls via `ROS2Command`):**

| Service | Type | Parameter |
|---|---|---|
| `magician_vision_classifier/set_fps` | `example_interfaces/srv/SetFloat64` | `target_fps` |
| `magician_vision_classifier/set_step` | `example_interfaces/srv/SetInt64` | `step_size` |
| `magician_vision_classifier/set_threshold` | `example_interfaces/srv/SetFloat64` | `threshold` |
| `magician_vision_classifier/set_majority_voting` | `std_srvs/srv/SetBool` | `majority_voting` |
| `magician_vision_classifier/set_two_stage` | `std_srvs/srv/SetBool` | `two_stage_enabled` |
| `magician_vision_classifier/reload_model` | `std_srvs/srv/Trigger` | (after model_path is set) |

---

## 6. File-Level Change List

### Files to modify

| File | Change summary |
|---|---|
| `app/engine/schema.py` | Add new questions (Section B and D extensions), add confidence categories 8 and 9 |
| `modules/grabber/compute.py` | Expand `run()` to process all grabber params from new questions; add `generate_yaml()` and `generate_launch_args()` helpers; write `params.yaml` and `launch_args.txt` to output dir |
| `modules/grabber/ros_interface.py` | Remove `ros2 param set` commands for startup-only params; instead return a file-reference command pointing to `params.yaml`; keep any truly dynamic params if added later |
| `modules/vision_classifier/compute.py` | Expand `run()` to process all classifier params; implement model-selection logic (check if `model_path` exists, else set `retrain_required=1`); write `training_config.json` and `live_config.json` to output dir |
| `modules/vision_classifier/ros_interface.py` | Add all service-call `ROS2Command` entries for runtime-tunable params (fps, step, threshold, majority voting, two-stage, reload_model) |

### Files to create

| File | Purpose |
|---|---|
| `modules/grabber/generate_config.py` | Helper: `generate_yaml(outputs) -> str` and `generate_launch_args(outputs) -> str` — separated from compute logic for testability |
| `modules/vision_classifier/generate_config.py` | Helper: `generate_training_config(outputs) -> dict` and `generate_live_config(outputs) -> dict` |

---

## 7. compute.py Logic — Decision Trees

### 7.1 Grabber compute logic

```
answers → outputs (flat dict)
    useCamera   = q2_camera_type != "none"
    useArduino  = "tactile" in q3_additional_sensors OR lighting_mode in [dlight, rlight, tlight]
    useTeensy   = "tactile" in q3_additional_sensors
    useATIForce = "tactile" in q3_additional_sensors
    streamData  = q2_stream_shm == true
    width, height = q2_camera_resolution
    frameRate   = q2_camera_framerate
    useRAM      = frameRate > 10
    exposure    = q2_camera_exposure
    gain        = q2_camera_gain
    blackLevel  = q2_camera_blacklevel
    atiIP       = q3_force_sensor_ip
    atiPort     = q3_force_sensor_port
    arduinoPath = q3_arduino_path
    teensyPath  = q3_teensy_path
    lightingMode = q3_lighting_mode
    cameraStreamName = q2_stream_shm_name (or "stream1")
    tactileStreamName = q3_tactile_stream (or "stream_tactile")
    → write params.yaml
    → write launch_args.txt
```

### 7.2 Vision Classifier compute logic

```
answers → outputs
    model       = q_clf_model (backbone name)
    tile_size   = q_clf_tile_size
    step_size   = q_clf_step_size
    threshold   = q_clf_threshold
    target_fps  = q_clf_fps
    majority_voting = q_clf_majority_voting
    two_stage   = q_clf_two_stage
    use_lasers  = q_clf_use_lasers
    laser_topics = q_clf_laser_topics
    laser_xy_pixels = q_clf_laser_pixels
    laser_idw_power = q_clf_laser_idw_power
    AoLP/DoLP/unpolarized = q_clf_aolp/dolp/unpolarized

    IF q_clf_model_path is set AND file exists:
        retrain_required = 0
        model_path = q_clf_model_path
    ELIF q_clf_dataset_dir is set:
        retrain_required = 1
        → write training_config.json
        → (future) invoke trainMagicianVisionClassifierTorch.py
        model_path = <expected output path from training>
    ELSE:
        retrain_required = 0
        model_path = "" (warn: no model available)

    → write live_config.json
```

---

## 8. Confidence Score Impact

New questions feed into existing and new confidence categories as follows:

| Existing category | New questions added |
|---|---|
| Camera/Sensors (id=2) | `q2_camera_resolution`, `q2_camera_framerate`, `q2_camera_exposure`, `q2_stream_shm` |
| Defect Types (id=5) | `q_clf_model`, `q_clf_tile_size`, `q_clf_threshold` |

New categories:

| New category | Questions |
|---|---|
| Grabber Hardware (id=8) | `q2_camera_framerate`, `q3_force_sensor_ip`, `q3_lighting_mode`, `q3_arduino_path`, `q3_teensy_path` |
| Classifier Config (id=9) | `q_clf_model`, `q_clf_tile_size`, `q_clf_threshold`, `q_clf_model_path`, `q_clf_use_lasers` |

The existing confidence bar for `grabber` and `vision_classifier` modules drives from categories 2+8 and 5+9 respectively.

---

## 9. Variability / Change Management

This integration is designed to stay in sync with upstream magician repositories by:

1. **Parameter tables are the single source of truth** — `generate_config.py` helpers build YAML/JSON from the tables above; adding a new upstream param means updating the helper and the schema question, not scattering changes across files.

2. **`bigmodel.json` schema is mirrored** — `generate_training_config()` writes a dict that exactly matches the `load_hyperparameters()` contract in `trainMagicianVisionClassifierTorch.py`. If the upstream adds a new key, only `generate_config.py` needs updating.

3. **Service names are constants** — `ros_interface.py` for the classifier declares service name strings at the top of the file, matching the `create_service(...)` calls in `liveClassifierTorchROS.py`. Upstream renames propagate in one place.

4. **`live_config.json` acts as a bridge** — until the file-level constants in `liveClassifierTorchROS.py` (LASER_TOPICS, LASER_XY_PIXELS, etc.) are promoted to ROS 2 params, the COT writes `live_config.json` and an operator step loads it. When they become proper params, the `ros_interface.py` service calls can replace that file with direct `ros2 param set` commands.

---

## 10. Implementation Sequence

Execute in this order to keep the app functional at each step:

1. **Schema** — add new question stubs to `app/engine/schema.py` (sections B and D). GUI renders them immediately; compute ignores unknown answers gracefully.
2. **Grabber compute** — expand `modules/grabber/compute.py` and create `modules/grabber/generate_config.py`; add YAML + launch_args output.
3. **Grabber ROS interface** — update `modules/grabber/ros_interface.py` to remove broken `param set` calls and reference the generated files.
4. **Classifier compute** — expand `modules/vision_classifier/compute.py` and create `modules/vision_classifier/generate_config.py`; add training_config.json + live_config.json output.
5. **Classifier ROS interface** — add all service-call commands to `modules/vision_classifier/ros_interface.py`.
6. **Confidence categories** — add new category entries to `schema.py` after compute tests pass.
7. **Integration test** — create a synthetic use case JSON with all new fields populated and verify both result.json files and all generated config files are correct.

---

## 11. Open Questions / Risks

| # | Item | Resolution needed |
|---|---|---|
| 1 | `liveClassifierTorchROS.py` file-level constants (LASER_TOPICS, etc.) are not ROS 2 params — COT can write a config file but cannot apply them live without a restart | Accept for now; note in live_config.json. Track upstream for param promotion. |
| 2 | Grabber node cannot accept `ros2 param set` at runtime — only startup YAML is useful | Confirmed — generate YAML only; no `param set` commands for grabber. |
| 3 | Training pipeline (`trainMagicianVisionClassifierTorch.py`) is a long-running GPU job — not suitable for synchronous COT compute | Keep `retrain_required` flag + generated config as trigger; actual training remains manual / CI step. |
| 4 | `q_clf_laser_pixels` involves 6 numeric inputs (3×x,y pairs) — the current questionnaire schema supports `text` and `number` types but not "array of coordinate pairs" | Either use 6 individual number fields or add a new `coordinate_array` question type in a schema extension. |
| 5 | `MAXIMUM_ALLOWED_EXPOSURE_IN_MICROSECONDS` is a compile-time constant not exposed as a param | Validate in compute.py with a sensible default cap (e.g. 50 000 µs) and warn if exceeded. |
