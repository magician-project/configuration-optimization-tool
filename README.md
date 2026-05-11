# Configuration Optimization Tool (COT)

Decision-support layer for configuring MAGICIAN robot modules to new use cases.  
Part of the MAGICIAN project — Phase 1 (Human-in-the-loop, rule-based recommendations).

---

## Running locally

**Prerequisites:** Python 3.10+, Node 18+, the `.venv` already created in the repo root.

### 1 — Backend (FastAPI)

```bash
# from repo root
cd backend
..\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

API runs at **http://localhost:8000**  
Interactive docs at **http://localhost:8000/docs**

### 2 — Frontend (React + Vite)

```bash
# second terminal, from repo root
npm --prefix frontend run dev
```

UI runs at **http://localhost:5173**

---

## What it does

1. Create a **use case** (e.g. "Boat hull inspection")
2. Fill in the **questionnaire** — 10 questions across 5 sections (robot setup, sensors, materials, defects, time constraints)
3. After saving, a banner shows which of the 5 MAGICIAN modules need action and takes you to the **Module Dashboard**
4. Each module tile shows the required action type (`retrain` / `reconfigure` / `review`) and any flags
5. Click a tile to see the full recommendation, acknowledge flags, and mark the module as **validated**
6. Once all impacted modules are validated, the **Deploy to ROS** button sends updates to the ROS framework (mocked in Phase 1)

---

## Project structure

```
backend/
  main.py                   FastAPI app entry point
  engine/
    questionnaire_engine.py Rule-based impact computation (all 10 questions)
    module_registry.py      Static definitions of the 5 MAGICIAN modules
    ros_adapter.py          ROS interface (MockROSAdapter by default)
  models/                   Pydantic models
  routers/                  use_cases, modules, deployment, questionnaire
  storage/json_store.py     JSON file persistence (one file per use case)
  data/use_cases/           Persisted use case files

frontend/
  src/
    pages/
      Home.tsx              Use case list + create
      UseCasePage.tsx       Questionnaire + Module Dashboard
    components/
      QuestionnaireForm.tsx Data-driven form (rendered from /questionnaire/schema)
      ModuleGrid.tsx        Dashboard tile grid
      ModuleTile.tsx        Module card with status + action badges
      ModuleDetail.tsx      Modal — impacts, flags, validate/acknowledge
      ConfidenceBar.tsx     7-category questionnaire completeness bar
      DeployButton.tsx      Gated deploy button
```

---

## Configuration

| Env var | Default | Effect |
|---------|---------|--------|
| `ROS_MOCK` | `true` | Set to `false` to use a real ROS adapter (not yet implemented) |

---

## MAGICIAN modules

| Module | ROS package |
|--------|-------------|
| Grabber | `magician_grabber` |
| Orienteering Solver | `op_solver` |
| Localiser | `localisation` |
| Tactile Classifier | `tactile_classifier_system` |
| Vision Classifier | `magician_vision_classifier` |
