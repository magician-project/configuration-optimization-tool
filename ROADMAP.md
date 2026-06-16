# COT 12-Month Development Roadmap
**Period:** July 2026 – June 2027  
**Capacity:** ~16 hours / month (solo developer) · ~48 h per quarter  
**Total budget:** ~192 hours  
**Top priority:** Feature completeness — all modules covered, artifacts generated correctly  
**Deployment target:** Local machine (no server/auth required this year)

---

## Constraints & Principles

| Constraint | Impact on planning |
|---|---|
| 16 h/month | Quarters are the unit of planning; individual months flex within a quarter |
| Solo developer | No parallel tracks; strict sequencing |
| No external deadline | Sequence by value, not by date |
| New modules may be added | Keep module code easy to copy (template-based), not plug-in framework |
| GUI = existing React app | Improve what exists; no platform switch |
| Light testing | Smoke tests + schema validation only; full unit test coverage only for critical helpers |
| ROS adapter = file-based | Generate `params.yaml` / config JSONs; no direct ROS connection this year |

---

## Overview

```
Q1  Jul – Sep 2026   First Setup      — all five modules have a working compute + config
Q2  Oct – Dec 2026   Refinement       — GUI polished, tests green, artifacts visible
Q3  Jan – Mar 2027   MVP              — cross-module logic, conflict detection, report export
Q4  Apr – Jun 2027   Production-ready — Docker, contributor guide, hardening, v1.0 tag
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

**Goal:** Q1 delivered raw functionality — Q2 makes it reliable and usable. A `make test` command catches regressions across all five modules. Every generated config file (params.yaml, training_config.json, etc.) is viewable and downloadable directly in the GUI. Parameter edge cases discovered during Q1 testing are fixed before they reach a demo. By end of Q2 the generated artifacts are verified to be executable on the ROS 2 framework.

### Q2-A — Smoke Test Suite
- Add `tests/` with pytest; schema smoke test (unique IDs, valid condition references); compute smoke test per module (expected output keys, sensible types); YAML/JSON validity check for generated artifacts
- Add `make test` target; document in `README.md`
- **Done when:** `make test` passes from a clean checkout with no additional setup

### Q2-B — Artifact Display in GUI
- List generated artifact files per module in the Module Detail view after compute
- "View" button opens file in a read-only, syntax-highlighted panel; "Copy" and "Download" actions available
- Show a banner when `retrain_required=1`; show `launch_args.txt` as a copyable code block
- **Done when:** An operator can view and copy all config files without touching the file system

### Q2-C — Schema & Engine Hardening
- Review all questions against real use: fix awkward conditions, missing option labels, or unclear question text discovered during Q1
- Ensure all five modules' impact rules are consistent: same action type naming, no orphaned flag IDs
- Extend confidence scoring if new questions were added in Q1
- **Done when:** No open schema TODOs; `make test` still passes after any fixes

### Q2-D — Module Parameter Sync
- Check each module's `generate_config.py` against its upstream repo for any parameter changes since the initial integration
- Update parameter tables in `magician_integration_plan.md` to reflect current state
- **Done when:** All five `generate_config.py` implementations match the current upstream parameter schemas

### Q2-E — ROS 2 Execution Readiness
- Validate that the generated `params.yaml` files are accepted by `ros2 run --params-file` without errors for grabber and localiser
- Validate that `ros2 service call` commands emitted by each `ros_interface.py` use the correct service names and message types against the actual running nodes
- Document the manual verification steps (node name, topic, expected response) in each module's `README.md`
- Update the Constraints & Principles table: ROS adapter moves from "file-based only" to "file-based + verified against live nodes"
- **Done when:** A developer can take the generated artifacts from any module and launch the corresponding ROS 2 node without manual parameter editing

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
- Add these to the `make test` suite
- **Done when:** All multi-module scenario tests pass in CI

### Q3-C — Configuration Report Export
- Add "Export Report" button to the use case page (visible after compute)
- Generate `configuration_report.json`: use case metadata, full answers, per-module impact summary, artifact paths, active conflict warnings
- Optionally generate a Markdown version; both downloadable from the GUI
- **Done when:** Clicking "Export Report" downloads a complete, self-contained configuration record

### Q3-D — UX Pass
- Walk through the full flow (create use case → fill questionnaire → compute → view artifacts → export report) and fix friction points
- Improve empty states, error messages, and loading indicators; ensure the confidence score is explained to the user
- **Done when:** A colleague unfamiliar with the codebase can complete the full flow without help

---

## Q4 — Production-Ready (Apr – Jun 2027)

**Goal:** The tool can be handed to a new developer or consortium partner with no setup friction. It is packaged, documented, and tagged as v1.0.

### Q4-A — Module Template & Contributor Guide
- Create `modules/_template/` with annotated `compute.py`, `generate_config.py`, `ros_interface.py`, and `README.md`
- Document the schema extension pattern and questionnaire engine impact rule pattern
- Update top-level `modules/README.md` to reference the template
- **Done when:** A new contributor can add a module by following the template with no prior codebase knowledge

### Q4-B — Docker Packaging
- Write multi-stage `Dockerfile` (Python backend + Node frontend build) and `docker-compose.yml`
- Verify the full flow works inside Docker; add a health-check endpoint to the backend
- Add Docker quick-start section to `README.md`
- **Done when:** `docker compose up` gives a fully functional tool with no manual setup

### Q4-C — Final Hardening & Backlog
- Fix regressions or edge cases discovered during Q3 real use
- Review all five modules against upstream repos one final time
- Address any remaining backlog items that fit within the time budget
- **Done when:** No known open bugs; all `make test` checks pass on a clean Docker build

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
| Q2 | Oct – Dec 2026 | Refinement — tests, GUI polish, parameter sync | ~48 h |
| Q3 | Jan – Mar 2027 | MVP — cross-module logic, conflict detection, export | ~48 h |
| Q4 | Apr – Jun 2027 | Production-ready — Docker, template, v1.0 | ~48 h |

**Total estimated hours:** ~192 h

---

## Backlog (deferred, not scheduled)

- **Multi-user / auth** — use case ownership, login, shared access
- **Real ROS 2 adapter** — direct ros2 service call / param set connection (requires hardware)
- **Cloud hosting** — make the tool accessible outside the local machine
- **Automated retraining trigger** — invoke `trainMagicianVisionClassifierTorch.py` from COT compute
- **Database backend** — replace JSON file storage with SQLite or PostgreSQL
- **Use case version history** — track changes to a single use case over time
- **Advanced UI polishing** — wizard flow, mobile layout, accessibility audit
- **Full integration tests** — HTTP → compute → GUI end-to-end coverage

---

## Risk Register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Upstream repos change parameter names | Medium | Each module's `generate_config.py` is the single update point; `magician_integration_plan.md` serves as reference |
| Module parameter research takes longer than expected | Medium | Q1 milestones include research time; defer non-critical params to Q2-D sync |
| 16 h/month is insufficient for a quarter milestone | Medium | Quarters have flex across 3 months; defer polish within the quarter rather than blocking |
| New modules added mid-roadmap | Low | Q4-A template provides a clear onboarding path |
| Solo developer absence | Low | Docker (Q4-B) + documented templates (Q4-A) reduce bus-factor risk |
