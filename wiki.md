# Configuration Optimization Tool — Wiki

## Overview

The Configuration Optimization Tool (COT) is a decision-support and orchestration desktop application developed as part of the MAGICIAN project to help engineers adapt the robot system to new or evolving inspection use cases. When an operator or systems engineer needs to deploy MAGICIAN for a different task — whether a minor variation of an existing job or a completely new inspection scenario — they do not need to manually trace through the robot software to figure out what needs changing. Instead, COT provides a guided, structured process that converts a use case description into concrete, actionable recommendations for each of the MAGICIAN software modules.

COT is a standalone Python desktop application built with PySide6. It does not run inside ROS and does not require a live ROS environment for its decision-making logic. This separation keeps the ROS runtime stable and predictable while giving COT full flexibility as an external orchestration tool.

---

## Architecture

COT is structured into four layers:

**`app/`** — Core application logic
- `engine/` — Questionnaire schema, rule-based impact computation, compute subprocess runner
- `models/` — Pydantic data models for use cases, questionnaire answers, module state, and ROS commands
- `ros/` — ROS 2 adapter layer (mock for development, real for deployment)
- `storage/` — JSON file persistence

**`gui/`** — PySide6 desktop interface
- `pages/` — Home page (use case list) and Use Case page (questionnaire + dashboard)
- `components/` — Reusable widgets: questionnaire form, module grid, module detail dialog, confidence bar, compute progress dialog

**`modules/`** — Per-module compute scripts and ROS interface definitions. Each module directory contains a `compute.py` (offline parameter derivation) and a `ros_interface.py` (ROS 2 command generation).

**`data/`** — Persisted use case files. Each use case lives in `data/use_cases/{id}/`, containing `use_case.json` and per-module compute output folders.

---

## The Questionnaire

The starting point for a new use case is the questionnaire. It is divided into five sections that together capture the key characteristics of a deployment scenario:

| Section | Topics covered |
|---------|---------------|
| A — Robot Configuration | Number of robot arms |
| B — Sensors & Perception | Camera type, resolution, frame rate, shared memory streaming, additional sensors, lighting |
| C — Material & Surface Properties | Material types, object size and dimensions, 3D mesh availability |
| D — Defect Detection | Defect types to detect |
| E — Time & Priority Constraints | Time window constraints, profit definition |

Each question directly reflects parameters and design choices that are known to affect one or more MAGICIAN modules. The schema is defined in `app/engine/schema.py` and serves as the single source of truth for both the GUI form renderer and the impact engine.

Module-specific configuration (for example, vision classifier model selection or ergodic control time budget) is stored separately in `UseCase.module_answers[module_id]` and is collected through the module detail dialog rather than the main questionnaire form.

### Confidence Score

A multi-category completeness bar shows how thoroughly the questionnaire has been filled in. Categories include: Robot Arms, Camera/Sensors, Lighting, Material/Size, Defect Types, Time/Profit, Mesh, Grabber Hardware, and Classifier Config. The score drives a low / medium / high confidence level displayed on each use case card.

---

## Impact Engine

When the user saves the questionnaire, `app/engine/questionnaire_engine.py` runs a rule-based impact computation. It evaluates each answer against rules derived from module owner input and produces a structured impact report per module. Each impact entry records:

- **characteristic** — the use-case property that triggered it
- **affects** — which aspect of the module is affected (Input, Process, Problem Description, etc.)
- **what_changes** — a human-readable explanation of what must be done
- **action_type** — `reconfigure`, `retrain`, or `review`
- **reason** — which question triggered this impact

Alongside impacts, the engine raises **flags** for cases where automated guidance is not sufficient and human oversight from a robotics engineer is explicitly required.

---

## Module Dashboard

The Module Dashboard shows all six MAGICIAN modules as tiles. Each tile communicates the module's current status and any active flags at a glance. The full module lifecycle is:

```
ok → needs_action → validated → computing → computed → deploying → deployed
                                                 ↓                     ↓
                                           compute_failed         deploy_failed
```

Clicking a tile opens the module detail dialog, where engineers can:
- Review all impact entries and the reasoning behind each
- Acknowledge flags that require human sign-off
- Configure module-specific parameters
- Validate the module (required before compute)
- Trigger the offline compute step

**Ergodic Control** is the only module that starts in `needs_action` by default (regardless of questionnaire answers), because trajectory planning always requires configuration.

---

## Offline Compute

For each module, COT can run a dedicated `compute.py` script that reads the questionnaire answers and derives the specific ROS parameter values without requiring a live ROS environment. The runner (`app/engine/compute_runner.py`) spawns the script as a child subprocess and streams its stdout/stderr back to a progress dialog in the GUI.

Computed outputs are written to:

```
data/use_cases/{id}/compute_outputs/{module_id}/
    result.json         Structured parameter values
    *.json              Any intermediate config files (e.g. kalman_config.json)
```

These files serve as the auditable source of truth for what will be sent to ROS. Module owners are responsible for providing `compute.py` scripts for their modules.

---

## ROS 2 Deployment

Once all impacted modules are validated and computed, the **Deploy to ROS** button becomes active. Deployment translates the computed parameter values into a list of `ROS2Command` objects (defined in `app/models/use_case.py`) and fires them via the ROS adapter layer:

- `ROS_MOCK=true` (default) — `MockROS2Adapter` logs the commands that would be sent without executing them. No ROS installation required.
- `ROS_MOCK=false` — `ROS2Adapter` executes `ros2 param set` and `ros2 service call` via subprocess, targeting specific nodes in the running ROS 2 environment.

Each module provides its own `ros_interface.py` that knows which ROS nodes and parameters map to the computed values.

---

## MAGICIAN Modules

### Grabber (`magician_grabber`)
Core sensor driver. Provides software access to all physical sensors on the Sensing Robot: GiGE Camera, ATI F/T Sensor, Teensy Accelerometer, Camera Light Controller, buttons, and ToF range finders. Impacted by changes to camera type, resolution, frame rate, additional sensor modalities, and lighting configuration.

### Orienteering Solver (`op_solver`)
Generates optimal schedules for cleaning robots to address defects. Determines the sequence of defects to visit and service time to spend at each. The problem variant shifts based on use-case characteristics: single arm → OP, no time constraint → TSP, multiple arms → TOP, time windows on defects → OPTW, custom profit definition → OPVP.

### Localiser (`localisation`)
Provides localisation of entities relative to the robot in the ROS 2 TF2 framework. Supports model-free localisation (approach 1) and model-based localisation (approaches 2 & 3, requiring a 3D mesh). Mesh availability and time constraints influence the localisation approach selection.

### Tactile Classifier (`tactile_classifier_system`)
Detects and classifies surface defects using tactile probe data (force, acceleration). Runs a CNN-LSTM / LSTM-CNN ensemble model. Must be retrained whenever materials, object sizes, or defect types change, because the underlying data distributions shift with these characteristics.

### Vision Classifier (`magician_vision_classifier`)
Visual defect detection and classification using camera images. Implicitly affected when new materials are introduced — the model must be retrained and the Vision Model Name parameter in the Configuration Module updated. Model selection, tile size, and confidence threshold are configured through the module detail panel.

### Ergodic Control (`magician_ergodic_control`)
Plans inspection trajectories that prioritise high-risk surface regions. Uses a Kalman filter to maintain a belief over defect distributions, combines historical data and welding process priors, then solves an ergodic control optimisation to generate end-effector waypoints on the 3D mesh. Always requires configuration; sensitive to mesh availability, time budget, and material/defect context.

---

## Data Persistence

Use cases are stored as JSON files under `data/use_cases/{id}/use_case.json`. The file contains:
- Use case metadata (id, name, created_at, updated_at)
- Questionnaire answers (`answers`)
- Module-specific configuration (`module_answers`)
- Full module state for all six modules (`modules`) including impacts, flags, compute results, and lifecycle timestamps
- Confidence score

When a use case is loaded and the registry contains modules that are not yet present in the stored file (e.g. after a new module is added to the codebase), the missing modules are inserted automatically with their default status.

---

## Development Notes

- COT is intentionally built outside the ROS framework. All decision logic runs without any ROS dependency.
- The questionnaire schema (`app/engine/schema.py`) is the single source of truth — the GUI form and the impact engine both read from it.
- Module-specific config questions live in `module_answers`, not in `QuestionnaireAnswers`, to keep the core questionnaire focused on use-case characteristics rather than module internals.
- Training pipelines for the Tactile Classifier and Vision Classifier (`train.py`) are present as placeholders; the interfaces and data flow are defined and waiting for the real training pipelines to be connected.
- Three modules — Body Pose Estimation, General Visual Perception, and LBD Multicamera Tracking — are present in the `modules/` directory as stubs and are not yet registered in the impact engine.