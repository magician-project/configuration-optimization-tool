# Module: Cartesian Controller

**ROS 2 node:** placeholder (`cartesian_controller_placeholder`) until IIT confirms the node name of the grinding runtime
**Action type:** Startup configuration (no retraining, no live tuning)
**Status:** _Implemented, not Verified_: the node name, parameter names and passing mechanism are not yet confirmed by IIT

## What this module does

The Cartesian Controller sequences the contact phases of a grinding cycle and generates the Cartesian
references for the robot: reach the starting pose of the primitive, the initial contact (TOUCH) phase,
the replay of the learned primitive, the unloading phase that releases the tool contact, and the final
retreat ("go away"). Force-dependent corrections come from the
[Impedance Controller](../impedance_controller/README.md); the learned pose profile comes from the
[DMP](../dmp/README.md). See [`CONTEXT.md`](../../CONTEXT.md) for these terms and
[`COT_CARTESIAN_CONTROLLER.md`](../../docs/specs/COT_CARTESIAN_CONTROLLER.md) for the IIT spec.

The Cartesian Controller is in scope when the pipeline selection includes grinding. It runs in the
same IIT grinding runtime as the DMP and the Impedance Controller, which is configured once at startup
and restarted to change ([ADR-0005](../../docs/adr/0005-iit-grinding-runtime-split-into-modules-with-one-startup-artifact.md)).

## File overview

| File | Purpose |
|---|---|
| `compute.py` | Reads the answers → resolves the startup configuration (spec defaults for anything unanswered) → writes `result.json` |
| `ros_interface.py` | Returns notes only: the real deploy goes through the IIT runtime, not `ros2 param set` |
| `test_compute.py` | Tests for the defaults, the fixed unload mode and the `result.json` contract |
| `README.md` | This file |

## Inputs (`module_answers["cartesian_controller"]`)

All parameters are optional: an unanswered one takes the spec default.

| Question key | Default | Description |
|---|---:|---|
| `reach_duration_s` | 10 s | Time allowed to reach the starting primitive pose |
| `touch_dwell_s` | 3 s | Dwell time of the initial contact phase |
| `touch_approach_distance_m` | 0.015 m | Bounds the tool travel towards the surface during TOUCH |
| `unload_tail_window_s` | 2.5 s | Limits the unloading logic to the end of the primitive |
| `unload_extra_duration_s` | 2.0 s | Extra time for a controlled contact release |
| `unload_retract_rate_m_s` | 0.015 m/s | Tool-normal retraction velocity while unloading |
| `go_away_distance_m` | 0.10 m | Final retraction distance after contact release |
| `go_away_duration_s` | 5 s | Time allotted to the final retreat |
| `control_rate_hz` | 1000 Hz | Update rate of the force control and the Cartesian references. Must be greater than 0 (minimum 1 Hz in the form). **Shared** with the Impedance Controller, which shows it read-only: this module owns it |

## Outputs (written to `result.json`)

`outputs` is flat (`str` or `float`): every key of the table above, plus:

| Key | Description |
|---|---|
| `unload_mode` | Always `"smooth retract"`; not a question |

## Deploy blockers

`deploy_blockers` in `result.json` names the cause:

- the control rate is not a finite number greater than 0 (also for a stored or imported answer that bypassed the form). The value is then left out of `outputs`.

Every other parameter has a default, so nothing else can be left incomplete.

## Notes

- Startup configuration: the grinding runtime must be restarted for changes to take effect.
- COT only compares the time constraint with one baseline cycle (see below) and never changes the phase
  durations; contact and safety requirements always take precedence.

## Use-case impact rules

These rules only apply while the module is in scope. They detect and explain; they never change a parameter.

- **Time constraint (Q9):** one defect cycle is estimated as `reach_duration_s + touch_dwell_s + max(baseline
  primitive duration of the selected classes) + unload_extra_duration_s + go_away_duration_s`, using the answers
  above (or their defaults). The baseline durations come from the [DMP](../dmp/README.md) and are "IIT baseline,
  not measured from configured primitive files". A cycle longer than the budget gives a feasibility flag;
  otherwise an impact states how many complete baseline cycles fit (e.g. 7 for the defaults and 5 minutes).
  That is not a prediction: the number of defects and the travel and scheduling time between them are not included.

Use-case characteristics without a question yet (**nog geen vraag**): robot / tool change and contact quality / loss.

## Open points

The node name, the literal parameter names, the passing mechanism and the valid ranges of the
parameters (the spec only gives baselines) are open questions for IIT; see "Open questions for IIT" in [`COT_DMP.md`](../../docs/specs/COT_DMP.md).
