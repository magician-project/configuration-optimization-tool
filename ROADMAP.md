# COT 12-Month Development Roadmap
**Period:** July 2026 – June 2027  
**Capacity:** ~16 hours / month (solo developer)  
**Total budget:** ~192 hours  
**Top priority:** Feature completeness — all modules covered, artifacts generated correctly  
**Deployment target:** Local machine (no server/auth required this year)

---

## Constraints & Principles

| Constraint | Impact on planning |
|---|---|
| 16 h/month | Each milestone must be completable independently; no multi-month in-progress work |
| Solo developer | No parallel tracks; strict sequencing |
| No external deadline | Sequence by value, not by date |
| New modules may be added | Keep module code easy to copy (template-based), not plug-in framework |
| GUI = existing React app | Improve what exists; no platform switch |
| Light testing | Smoke tests + schema validation only; full unit tests only for critical helpers |
| ROS adapter = file-based | Generate `params.yaml` / config JSONs; no direct ROS connection this year |

---

## Milestone Overview

```
Month  1   M2 — GUI: render new questions (conditional B/D extension)
Month  2   M3 — Localiser module integration
Month  3   M4 — Tactile sensor module integration
Month  4   M5 — Orienteering solver module integration
Month  5   M6 — Smoke test suite + schema validation CI
Month  6   M7 — Deploy artifact display in GUI
Month  7   M8 — Questionnaire engine: cross-module dependencies & conflict detection
Month  8   M9 — Module template & contributor guide (new-module workflow)
Month  9   M10 — Export / configuration report (PDF or structured JSON)
Month 10   M11 — Docker packaging + local install script
Month 11   M12 — Hardening, backlog, and retrospective
```

---

## Detailed Milestones

### M2 — GUI: Conditional Question Rendering
**Month:** Month 1 (July 2026) | **Budget:** 16 h

**Context:** The React form renders questions from the schema. The new questions have `condition` fields (e.g. show `q3_force_sensor_ip` only when `tactile` is selected in `q3_additional_sensors`). The current renderer ignores these conditions, so all 50 questions are visible simultaneously.

**Work items:**
- Update `gui/components/questionnaire_form.py` (or the React equivalent) to evaluate `condition` fields on each question and hide/show accordingly
- Handle the three condition operators used in the schema: `value`, `contains`, `empty`, `in`
- Ensure follow-up questions (existing `follow_up` pattern) continue to work alongside the new `condition` pattern
- Visual grouping: add a subtle separator or label when transitioning from the original questions to the new Magician-specific questions within a section
- Smoke test: click through Section B and D with different sensor combinations; verify only relevant questions appear

**Done when:** The form hides irrelevant fields and shows only contextually appropriate questions.

---

### M3 — Localiser Module Integration
**Month:** August 2026 | **Budget:** 16 h

**Context:** `modules/localiser/` has stub `compute.py` and `ros_interface.py`. The localiser module determines how the robot maps its environment and tracks object positions.

**Work items:**
- Research: identify localiser parameters from the magician-project repository (equivalent of what we did for grabber/classifier)
- Add new schema questions to Section A or B for localiser-specific config (map resolution, tracking mode, reference frame, etc.)
- Implement `modules/localiser/compute.py` — derive outputs from answers
- Create `modules/localiser/generate_config.py` — write a `localiser_config.json` artifact
- Implement `modules/localiser/ros_interface.py` — param and service calls for `/magician_localiser`
- Update questionnaire engine impact rules for localiser
- Update confidence categories to include localiser fields

**Done when:** A use case with localiser answers produces a `localiser_config.json` and correct ROS commands.

---

### M4 — Tactile Sensor Module Integration
**Month:** September 2026 | **Budget:** 16 h

**Context:** `modules/tactile_sensor/` is a stub. The tactile sensor (ATI NetFT + Teensy accelerometer) has hardware overlap with the grabber and a dedicated `train.py` for force-based defect detection.

**Work items:**
- Research: identify tactile sensor parameters (window size, feature extraction settings, force thresholds, training data path)
- Add schema questions for tactile-specific config — note that `useATIForce` and `useTeensy` are already captured via grabber; focus on tactile *processing* parameters
- Implement `modules/tactile_sensor/compute.py` and `generate_config.py`
- Handle the grabber/tactile dependency: if `tactile_sensor` is active, grabber compute must also set `useATIForce=True` and `useTeensy=True` — implement cross-module constraint checking
- Implement `modules/tactile_sensor/ros_interface.py`
- Update questionnaire engine for tactile impacts

**Done when:** A use case with force sensing enabled produces correct tactile config and the grabber config reflects the dependency.

---

### M5 — Orienteering Solver Module Integration
**Month:** October 2026 | **Budget:** 16 h

**Context:** `modules/orienteering_solver/` is a stub. This module plans inspection paths optimising coverage and defect-finding profit.

**Work items:**
- Research: identify orienteering solver parameters (profit weights, path constraints, time budget, mesh input path)
- Add schema questions — note that `q9_time` and `q10_profit` are already in Section E; add orienteering-specific follow-up questions there
- Implement `modules/orienteering_solver/compute.py` and `generate_config.py`
- Implement `modules/orienteering_solver/ros_interface.py`
- Update questionnaire engine for orienteering solver impacts

**Done when:** A use case with time/profit constraints produces an orienteering solver config with correct path parameters.

---

### M6 — Smoke Test Suite
**Month:** November 2026 | **Budget:** 16 h

**Context:** After 5 modules are integrated, regressions become more likely. Light testing only — no full coverage.

**Work items:**
- Add `tests/` directory with pytest setup
- Schema smoke test: verify all question IDs are unique, all `condition.field` references point to existing question IDs, all `confidence_categories` field references are valid
- Compute smoke test: for each module, run `compute.run()` with a fully-populated synthetic answers dict and assert the output dict has all expected keys and sensible types
- Config generation smoke tests: for grabber, assert `generate_yaml()` produces valid YAML; for classifier, assert `generate_training_config()` produces a dict matching the `bigmodel.json` required keys
- CI setup: add a `Makefile` target `make test` that runs the suite; document it in `README.md`

**Done when:** `make test` passes from a clean checkout with no additional setup.

---

### M7 — GUI: Deploy Artifact Display
**Month:** December 2026 | **Budget:** 16 h

**Context:** After compute runs, each module now writes artifact files (params.yaml, training_config.json, live_config.json, launch_args.txt). The GUI currently has no way to show or download these.

**Work items:**
- After compute completes, list artifact files per module in the Module Detail view
- Add "View" button that opens the file content in a read-only text panel (syntax-highlighted YAML/JSON)
- Add "Copy to clipboard" and "Download" actions per artifact file
- Show a clear banner when `retrain_required=1` explaining the operator must run training manually before deploying
- Show launch_args.txt content as a copyable code block with a label "Run this command to start the grabber"

**Done when:** An operator can see and copy all generated config files from the GUI without opening a file explorer.

---

### M8 — Cross-Module Dependencies & Conflict Detection
**Month:** January 2027 | **Budget:** 16 h

**Context:** Some parameter choices conflict across modules (e.g. tile_size in classifier must match the annotator's dataset tiling; grabber framerate > 10 Hz requires use_ram; tactile sensor requires grabber's ATI/Teensy flags). These are currently silent.

**Work items:**
- Define a `cross_module_rules` structure in the questionnaire engine (or a new `app/engine/conflict_checker.py`) listing known inter-module constraints
- Implement conflict checking after compute: return a list of warnings/errors per use case
- Surface conflicts in the GUI: yellow warning badge on affected module tiles; detail view lists the conflict and the two parameters involved
- Initial rule set (at minimum):
  - `frame_rate > 10` → `use_ram` must be true (grabber)
  - `use_ati_force=True` → `tactile_sensor` module must also be active
  - `tile_size` (classifier) should match dataset tile size if dataset_dir is provided
  - `stream_data=False` → classifier cannot receive frames (streaming is required for live inference)

**Done when:** A use case with a known conflict shows a visible warning in the GUI with a plain-language explanation.

---

### M9 — Module Template & Contributor Guide
**Month:** February 2027 | **Budget:** 16 h

**Context:** New modules may be added. A clear template and guide will let future contributors (or future-you) add a module correctly without reverse-engineering existing code.

**Work items:**
- Create `modules/_template/` with:
  - `__init__.py`
  - `compute.py` — annotated template with all required function signatures and doc strings
  - `generate_config.py` — template for writing config artifacts
  - `ros_interface.py` — template showing how to add param + service commands
  - `README.md` — step-by-step guide: "how to add a new module"
- Update top-level `modules/README.md` to reference the template
- Document the schema extension pattern: how to add questions, conditions, and confidence categories for a new module
- Document the questionnaire engine: how to add impact rules for new questions

**Done when:** A new contributor can add a new module following the template with no knowledge of the existing codebase.

---

### M10 — Configuration Report Export
**Month:** March 2027 | **Budget:** 16 h

**Context:** Operators and MAGICIAN partners need a shareable record of a configuration decision: what answers were given, what modules are impacted, what artifacts were generated.

**Work items:**
- Add "Export Report" button to the use case page (visible once compute is complete)
- Generate a structured JSON report (`configuration_report.json`) containing:
  - Use case metadata (name, created_at, computed_at)
  - Full answers dict
  - Per-module: impact type, confidence score, outputs summary, artifact file paths, validation status
  - Any active conflict warnings
- Optionally generate a human-readable Markdown version of the same report
- Download both files directly from the GUI

**Done when:** Clicking "Export Report" downloads a JSON (and optional Markdown) file containing the full configuration context.

---

### M11 — Docker Packaging
**Month:** April 2027 | **Budget:** 16 h

**Context:** Currently the tool requires manual Python venv setup + npm install. A Docker image makes it portable and shareable within the MAGICIAN consortium even if still running locally.

**Work items:**
- Write `Dockerfile` (multi-stage: Python backend + Node frontend build)
- Write `docker-compose.yml` with a single `docker compose up` workflow
- Update `README.md` with Docker quick-start section
- Verify the full flow (create use case → fill questionnaire → compute → view artifacts) works inside Docker
- Add a health check endpoint to the backend

**Done when:** A colleague can run `docker compose up` and use the full tool without any Python/Node setup.

---

### M12 — Hardening, Backlog & Retrospective
**Month:** May 2027 | **Budget:** 16 h

**Context:** Final month for cleanup, deferred items, and planning the next cycle.

**Work items (flexible — fill from backlog):**
- Fix any regressions or issues discovered during M1–M11
- Address schema edge cases found through real use: missing question types, awkward conditional flows, etc.
- Review all five module `compute.py` implementations against their upstream repos for any parameters added in the past year
- Write a brief retrospective noting what was built, what was deferred, and what the next 12-month priorities should be
- Tag a `v1.0` release in git with a `CHANGELOG.md`

**Done when:** The codebase is tagged, documented, and the next roadmap cycle is outlined.

---

## Budget Summary

| Month | Milestone | Focus area |
|---|---|---|
| Jul 2026 | M2 | Frontend — conditional rendering |
| Aug 2026 | M3 | Module — localiser |
| Sep 2026 | M4 | Module — tactile sensor |
| Oct 2026 | M5 | Module — orienteering solver |
| Nov 2026 | M6 | Quality — smoke tests |
| Dec 2026 | M7 | Frontend — artifact display |
| Jan 2027 | M8 | Backend — conflict detection |
| Feb 2027 | M9 | Extensibility — module template |
| Mar 2027 | M10 | Output — report export |
| Apr 2027 | M11 | DevOps — Docker |
| May 2027 | M12 | Hardening + retrospective |
| Jun 2027 | — | (Buffer / overflow month) |

**Total estimated hours:** 192 h (12 × 16 h)

---

## Backlog (deferred, not scheduled)

Items that are desirable but did not fit the 12-month budget:

- **Multi-user / auth** — use case ownership, login, shared access
- **Real ROS 2 adapter** — direct ros2 service call / param set connection (requires hardware access)
- **Cloud hosting** — make the tool accessible outside the local machine
- **Automated retraining trigger** — call `trainMagicianVisionClassifierTorch.py` directly from COT compute
- **Database backend** — replace JSON file storage with SQLite or PostgreSQL for better querying
- **Version control of use cases** — track history of changes to a single use case over time
- **Advanced UI polishing** — wizard flow, mobile layout, accessibility audit
- **Integration tests** — end-to-end tests covering the full HTTP → compute → GUI flow

---

## Risk Register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Upstream magician repos change parameter names | Medium | Each module's `generate_config.py` is the single place to update; parameter tables in `magician_integration_plan.md` serve as a reference |
| Localiser/tactile/orienteering param discovery takes longer than 1 month | Medium | Scope M3–M5 to include research; defer non-critical params to the backlog rather than blocking the milestone |
| 16 h/month is insufficient for a milestone | Medium | Each milestone is scoped for 16 h; if overrun, defer polish to M12 and mark the core deliverable as done |
| New modules added mid-roadmap | Low | M9 (template) provides a clear onboarding path; new module can slot into the next available month |
| Solo developer absence | Low | Docker (M11) + documented templates (M9) reduce bus-factor risk |
