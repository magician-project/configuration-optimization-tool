---
type: roadmap
period: 2026-07 to 2027-06
tags:
  - roadmap
  - planning
related:
  - "[[CONTEXT]]"
  - "[[magician_integration_plan]]"
---

# COT 12-Month Development Roadmap
**Period:** July 2026 – June 2027  
**Capacity:** ~16 hours / month (solo developer) · ~48 h per quarter  
**Total budget:** ~192 hours  
**Deployment target:** A locally deployable tool, independently installable by a new MAGICIAN developer or consortium partner — not a centrally hosted, multi-user service. No auth/RBAC/multi-user this year.

**Leading priority per quarter** (feature completeness is the Q1 priority, not the whole roadmap's):

| Quarter | Leading priority |
|---|---|
| Q1 | Completeness — cover all relevant modules, produce real configuration output |
| Q2 | Reliability & usability — make existing functionality trustworthy, usable, executable |
| Q3 | System integration / MVP — bring modules together, surface cross-module conflicts, integrated workflow |
| Q4 | Transferability & release readiness — packaging, documentation, handover toward v1.0 |

Feature completeness remains a standing constraint after Q1 (missing module functionality still needs fixing), but "add more features/modules" is no longer the leading priority once Q1 ends.

---

## Constraints & Principles

| Constraint | Impact on planning |
|---|---|
| 16 h/month | Quarters are the unit of planning; individual months flex within a quarter |
| Solo developer | No parallel tracks; strict sequencing |
| No external deadline | Sequence by value, not by date |
| New modules may be added | Keep module code easy to copy (template-based), not plug-in framework |
| GUI = existing PySide6 desktop app | Improve what exists; no platform switch, no server process |
| Light testing | Smoke tests + schema validation only; full unit test coverage only for critical helpers |
| ROS adapter = Implemented, not yet Verified | `app/ros/ros2_adapter.py` already fires real `ros2 param set` / `service call` commands; Q2-E verifies it against live nodes rather than building it from scratch |

---

## Overview

```
Q1  Jul – Sep 2026   First Setup      — all modules have a working compute + config
Q2  Oct – Dec 2026   Refinement       — GUI polished, tests green, artifacts visible, grinding modules added
Q3  Jan – Mar 2027   MVP              — cross-module logic, conflict detection, report export, Skeleton Tracker
Q4  Apr – Jun 2027   Production-ready — pip package, contributor guide, hardening, v1.0 tag
```

---

## Q1 — First Setup (Jul – Sep 2026)

**Goal:** Every module in the codebase produces real output. By end of Q1 you can fill in the questionnaire and get a config file out of every module.

### Q1-A — GUI: Conditional Question Rendering
- Evaluate `condition` and `follow_up` fields per question in the form renderer; hide/show questions dynamically
- Handle operators: `value`, `contains`, `empty`, `in`
- **Done when:** Filling in Section B with different sensor choices shows/hides the right follow-up fields

### Q1-B — Localiser Module
- Research localiser parameters from the magician-project repo; add schema questions for map resolution, tracking mode, reference frame
- Implement `modules/localiser/compute.py`, `generate_config.py`, `ros_interface.py`
- Update questionnaire engine impact rules and confidence categories for localiser
- **Done when:** A use case with localiser answers produces a `localiser_config.json` and correct ROS commands

### Q1-C — Tactile Sensor Module
- Research tactile processing parameters (window size, force thresholds, training data path); add schema questions
- Implement `modules/tactile_sensor/compute.py`, `generate_config.py`, `ros_interface.py`
- Note: `useATIForce` / `useTeensy` are already captured via grabber — focus on tactile-specific processing params
- **Done when:** A use case with tactile sensing produces a tactile config and grabber config reflects the ATI/Teensy dependency

### Q1-D — Orienteering Solver Module
- Research solver parameters (profit weights, path constraints, time budget, mesh path); add schema follow-up questions to Section E
- Implement `modules/orienteering_solver/compute.py`, `generate_config.py`, `ros_interface.py`
- **Done when:** A use case with time/profit constraints produces an orienteering solver config

---

## Q2 — Refinement (Oct – Dec 2026)

**Goal:** Q1 delivered raw functionality — Q2 makes it reliable and usable. A single `pytest` run catches regressions across all modules. Every generated config file (params.yaml, training_config.json, etc.) is viewable and can be copied or saved directly from the GUI. Parameter edge cases discovered during Q1 testing are fixed before they reach a demo. By end of Q2 the generated artifacts are verified to be executable on the ROS 2 framework.

### Q2-A — Smoke Test Suite
- Extend the existing pytest suite in `tests/`: schema smoke test (unique IDs, valid condition references); compute smoke test per module (expected output keys, sensible types); YAML/JSON validity check for generated artifacts
- Document how to run the tests (`pytest`) in `README.md`
- **Done when:** `pytest` passes from a clean checkout with no additional setup

### Q2-B — Artifact Display in GUI
- List generated artifact files per module in the Module Detail view after compute
- "View" button opens file in a read-only, syntax-highlighted panel; "Copy" and "Save as…" actions available
- Show a banner when `retrain_required=1`; show `launch_args.txt` as a copyable code block
- **Done when:** An operator can view and copy all config files without touching the file system

### Q2-C — Schema & Engine Hardening
- Review all questions against real use: fix awkward conditions, missing option labels, or unclear question text discovered during Q1
- Ensure all modules' impact rules are consistent: same action type naming, no orphaned flag IDs
- Extend confidence scoring if new questions were added in Q1
- **Done when:** No open schema TODOs; `pytest` still passes after any fixes

### Q2-D — Module Parameter Sync
- Check each module's `generate_config.py` against its upstream repo for any parameter changes since the initial integration
- Update parameter tables in [[magician_integration_plan]] to reflect current state
- **Done when:** Every module's `generate_config.py` matches the current upstream parameter schema

### Q2-E — ROS 2 Execution Readiness
- Validate that the generated `params.yaml` files are accepted by `ros2 run --params-file` without errors for grabber and localiser
- Validate that `ros2 service call` commands emitted by each `ros_interface.py` use the correct service names and message types against the actual running nodes
- Document the manual verification steps (node name, topic, expected response) in each module's `README.md`
- Update the Constraints & Principles table: ROS adapter moves from "Implemented, not yet Verified" to "Verified" (see [[CONTEXT]] for the maturity ladder)
- **Done when:** A developer can take the generated artifacts from any module and launch the corresponding ROS 2 node without manual parameter editing

### Q2-F — Grinding Modules: DMP, Impedance Controller, Cartesian Controller
- Add the three grinding modules to the module registry, based on the partner module scans
- DMP: select the learned grinding primitive per defect class (see [[CONTEXT]]); new demonstrations mean the primitive is regenerated and validated outside COT, never retrained
- Impedance Controller and Cartesian Controller: capture their configurable parameters and use-case impacts from the partner module scans
- Generate one shared startup configuration for the IIT grinding runtime that hosts all three (see [[0005-iit-grinding-runtime-split-into-modules-with-one-startup-artifact|ADR-0005]]); only fire live ROS 2 parameter updates once runtime tuning is confirmed for these modules
- Add schema questions, impact rules and module dependencies (DMP → Cartesian / Impedance Controller); in scope whenever the pipeline selection includes grinding. DMP joins Motion Planning; the two controllers form a new Controller group
- Broken into tickets 07–15 in `docs/tickets/`
- **Done when:** A grinding use case shows the three modules on the dashboard with impacts, and produces one startup configuration for the IIT grinding runtime

---

## Q3 — MVP (Jan – Mar 2027)

**Goal:** The tool behaves like a real product. Multiple modules talk to each other, conflicts surface automatically, and the output is shareable.

### Q3-A — Cross-Module Conflict Detection
- Implement `app/engine/conflict_checker.py` with a `cross_module_rules` list
- Initial rules: `frame_rate > 10 → use_ram required`; `use_ati_force → tactile_sensor must be active`; `stream_data=False → classifier cannot run live`; `tile_size must match dataset tiling`
- Surface conflicts in GUI: warning badge on module tile, plain-language explanation in detail view
- **Done when:** A use case with a known conflict shows a visible warning with the two parameters involved

### Q3-B — Cross-Module Integration Tests
- Write end-to-end compute tests that fill answers for two or more modules simultaneously and assert the combined outputs are consistent
- Cover at least 3 multi-module scenarios that exercise the conflict rules from Q3-A
- Add these to the pytest suite
- **Done when:** All multi-module scenario tests pass with `pytest`

### Q3-C — Configuration Report Export
- Add "Export Report" button to the use case page (visible after compute)
- Generate `configuration_report.json`: use case metadata, full answers, per-module impact summary, artifact paths, active conflict warnings
- Optionally generate a Markdown version; both saved via a "Save as…" dialog
- **Done when:** Clicking "Export Report" saves a complete, self-contained configuration record

### Q3-D — UX Pass
- Walk through the full flow (create use case → fill questionnaire → compute → view artifacts → export report) and fix friction points
- Improve empty states, error messages, and loading indicators; ensure the confidence score is explained to the user
- **Done when:** A colleague unfamiliar with the codebase can complete the full flow without help

### Q3-E — Skeleton Tracker Module
- Collect the partner module scan (inputs, outputs, configuration parameters, use-case effects), as was done for the grinding modules
- Add the Skeleton Tracker as a shared/safety module that is context-dependent: it is in scope only when the use case needs human tracking, not by default
- Model its dependency chain: Skeleton Tracker → Motion Forecaster → Motion Planner
- **Done when:** A use case with humans in the work cell brings the Skeleton Tracker into scope, with impacts and a generated configuration

---

## Q4 — Production-Ready (Apr – Jun 2027)

**Goal:** The tool can be handed to a new developer or consortium partner with no setup friction. It is packaged, documented, and tagged as v1.0.

### Q4-A — Module Template & Contributor Guide
- Create `modules/_template/` with annotated `compute.py`, `generate_config.py`, `ros_interface.py`, and `README.md`
- Document the schema extension pattern and questionnaire engine impact rule pattern
- Update top-level [[modules/README]] to reference the template
- **Done when:** A new contributor can add a module by following the template with no prior codebase knowledge

### Q4-B — pip Packaging
- Add a `pyproject.toml` that makes the COT an installable Python package, with a `cot` command that launches the desktop app
- Ship the module scripts and questionnaire schema as package data; keep use-case data in a user data folder instead of the install folder
- Verify that it installs into a ROS 2 Python environment, so the real ROS 2 adapter works without extra steps
- Replace the README setup steps with a `pip install` quick start
- **Done when:** `pip install` followed by `cot` gives a fully functional tool on a clean machine, with no manual setup

### Q4-C — Final Hardening & Backlog
- Fix regressions or edge cases discovered during Q3 real use
- Review all modules against upstream repos one final time
- Address any remaining backlog items that fit within the time budget
- **Done when:** No known open bugs; `pytest` passes on a clean `pip install`

### Q4-D — v1.0 Release
- Write `CHANGELOG.md` covering everything built across Q1–Q4
- Tag `v1.0` in git
- Write a brief retrospective: what was built, what was deferred, next 12-month priorities
- **Done when:** The repo has a `v1.0` tag, a `CHANGELOG.md`, and a next-cycle outline

---

## Budget Summary

| Quarter | Period | Theme | Budget |
|---|---|---|---|
| Q1 | Jul – Sep 2026 | First Setup — all modules producing output | ~48 h |
| Q2 | Oct – Dec 2026 | Refinement — tests, GUI polish, parameter sync, grinding modules | ~48 h |
| Q3 | Jan – Mar 2027 | MVP — cross-module logic, conflict detection, export, Skeleton Tracker | ~48 h |
| Q4 | Apr – Jun 2027 | Production-ready — pip package, template, v1.0 | ~48 h |

**Total estimated hours:** ~192 h

---

## Backlog (deferred, not scheduled)

- **Multi-user / auth** — use case ownership, login, shared access
- **Verified / Supported ROS 2 adapter** — `app/ros/ros2_adapter.py` is already *Implemented* (it fires real `ros2 param set` / `service call` subprocess commands); it is not yet *Verified* against a live ROS 2 environment or *Supported* as a release capability. Q2-E is the work that moves it up the maturity ladder — see [[CONTEXT]] for the Implemented/Verified/Supported terms.
- **Cloud hosting** — make the tool accessible outside the local machine
- **Automated retraining trigger** — invoke `trainMagicianVisionClassifierTorch.py` from COT compute
- **Database backend** — replace JSON file storage with SQLite or PostgreSQL
- **Use case version history** — track changes to a single use case over time
- **Advanced UI polishing** — wizard flow, high-DPI / small-screen layout, accessibility audit
- **Full integration tests** — questionnaire → compute → deploy end-to-end coverage through the GUI

---

## Risk Register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Upstream repos change parameter names | Medium | Each module's `generate_config.py` is the single update point; [[magician_integration_plan]] serves as reference |
| Module parameter research takes longer than expected | Medium | Q1 milestones include research time; defer non-critical params to Q2-D sync |
| 16 h/month is insufficient for a quarter milestone | Medium | Quarters have flex across 3 months; defer polish within the quarter rather than blocking |
| New modules added mid-roadmap | High — DMP, Impedance Controller and Cartesian Controller (Q2-F) and Skeleton Tracker (Q3-E) are now planned | Defer polish within the quarter rather than blocking; Q4-A template provides a clear onboarding path for later modules |
| Solo developer absence | Low | pip package (Q4-B) + documented templates (Q4-A) reduce bus-factor risk |
