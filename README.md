# Configuration Optimization Tool (COT)

Decision-support desktop application for configuring MAGICIAN robot modules to new use cases.  
Part of the MAGICIAN project — Phase 1 (Human-in-the-loop, rule-based recommendations).

---

## Running locally

**Prerequisites:** Python 3.10+, a `.venv` created in the repo root with dependencies installed.

### 1 — Install dependencies

```bash
# from repo root
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS
pip install -r requirements.txt
```

### 2 — Run the application

```bash
python app/main.py
```

The desktop GUI opens directly. No server process is needed.

---

## What it does

1. Create a **use case** (e.g. "Boat hull inspection") from the home screen
2. Fill in the **questionnaire** — questions across 5 sections (robot setup, sensors, materials, defects, time constraints)
3. Save answers → COT runs its rule-based impact engine and updates the **Module Dashboard**
4. Each module tile shows the required action type (`retrain` / `reconfigure` / `review`) and any flags
5. Click a tile to see the full impact list, acknowledge flags, and configure module-specific parameters
6. Mark the module as **validated**, then run the offline **Compute** step to derive exact ROS parameter values
7. Once all impacted modules are computed and validated, **Deploy to ROS** fires the changes to the ROS 2 framework

---

## Project structure

```
app/
  main.py                     Entry point — launches the PySide6 desktop app
  engine/
    questionnaire_engine.py   Rule-based impact computation
    module_registry.py        Static definitions of the 6 MAGICIAN modules
    compute_runner.py         Subprocess runner for per-module compute scripts
    schema.py                 Questionnaire schema (single source of truth)
  models/
    questionnaire.py          QuestionnaireAnswers Pydantic model
    use_case.py               UseCase, ModuleState, ModuleImpact, Flag, etc.
  ros/
    mock_adapter.py           Mock ROS 2 adapter (logs commands, no ROS required)
    ros2_adapter.py           Real ROS 2 adapter (subprocess ros2 param set / service call)
  storage/
    json_store.py             JSON file persistence (one folder per use case)

gui/
  main_window.py              Top-level QMainWindow, navigation between pages
  components/
    questionnaire_form.py     Data-driven form rendered from schema.py
    module_grid.py            Module Dashboard tile grid
    module_detail.py          Detail dialog — impacts, flags, validate / compute
    confidence_bar.py         Multi-category questionnaire completeness bar
    compute_progress_dialog.py  Live log output during offline compute
  pages/
    home_page.py              Use case list + create new use case
    use_case_page.py          Questionnaire tab + Module Dashboard tab

modules/
  grabber/                    Sensor driver compute & ROS interface
  ergodic_control/            Trajectory planning compute & ROS interface
  orienteering_solver/        Scheduling solver compute & ROS interface
  localiser/                  Localisation compute & ROS interface
  motion_planning/            Motion planning compute & ROS interface
  tactile_sensor/             Tactile classifier compute & training
  vision_classifier/          Vision classifier compute & training

data/
  use_cases/{id}/
    use_case.json             Persisted use case (answers, module states, results)
    compute_outputs/{module}/ Offline compute artefacts (configs + result.json)
```

---

## Configuration

| Env var | Default | Effect |
|---------|---------|--------|
| `ROS_MOCK` | `true` | Set to `false` to use the real ROS 2 adapter (requires a live ROS 2 environment) |

---

## MAGICIAN modules

| Module | ROS package | Action types |
|--------|-------------|--------------|
| Grabber | `magician_grabber` | reconfigure, review |
| Orienteering Solver | `op_solver` | reconfigure |
| Localiser | `localisation` | reconfigure, review |
| Tactile Classifier | `tactile_classifier_system` | retrain, reconfigure |
| Vision Classifier | `magician_vision_classifier` | retrain |
| Ergodic Control | `magician_ergodic_control` | reconfigure |

---

## Module lifecycle

```
ok → needs_action → validated → computing → computed → deploying → deployed
                                                 ↓                     ↓
                                           compute_failed         deploy_failed
```
