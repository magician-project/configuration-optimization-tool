# Module: Impedance Controller

**ROS 2 node:** placeholder (`impedance_controller_placeholder`) until IIT confirms the node name of the grinding runtime
**Action type:** Startup configuration (no retraining, no live tuning)
**Status:** _Implemented, not Verified_: the node name, parameter names and passing mechanism are not yet confirmed by IIT

## What this module does

The Impedance Controller regulates the normal contact force during grinding. It scales the learned
normal-force reference from the [DMP](../dmp/README.md), compares it with the measured wrench and turns
the normal-force error into a corrective TCP-normal velocity (admittance law), with feedforward for
changes in the desired force. The correction is added to the references of the
[Cartesian Controller](../cartesian_controller/README.md). Displacement, velocity and force limits keep
the contact safe; exceeding the maximum contact force triggers emergency termination. See
[`CONTEXT.md`](../../CONTEXT.md) for these terms and
[`COT_IMPEDANCE_CONTROLLER.md`](../../docs/specs/COT_IMPEDANCE_CONTROLLER.md) for the IIT spec.

The Impedance Controller is in scope when the pipeline selection includes grinding. It runs in the
same IIT grinding runtime as the DMP and the Cartesian Controller, which is configured once at startup
and restarted to change ([ADR-0005](../../docs/adr/0005-iit-grinding-runtime-split-into-modules-with-one-startup-artifact.md)).

## File overview

| File | Purpose |
|---|---|
| `compute.py` | Reads the answers → resolves the startup configuration (spec defaults for anything unanswered) → writes `result.json` |
| `ros_interface.py` | Returns notes only: the real deploy goes through the IIT runtime, not `ros2 param set` |
| `test_compute.py` | Tests for the defaults, force sync, the shared control rate and the `result.json` contract |
| `README.md` | This file |

## Inputs (`module_answers["impedance_controller"]`)

All parameters are optional: an unanswered one takes the spec default, except the measured wrench source (see below).

| Question key | Default | Description |
|---|---:|---|
| `force_reference_scale` | 1.0 | Scales the learned normal-force reference before execution |
| `control_rate_hz` | 1000 Hz | **Shared, read-only here:** owned by the [Cartesian Controller](../cartesian_controller/README.md) and read from its answers |
| `admittance_gain` | 0.0013 m/(N·s) | Converts normal-force error into corrective TCP-normal velocity |
| `force_rate_ff_scale` | 0.6 | Weights the feedforward for desired-force changes |
| `max_reference_force_rate` | 220 N/s | Limits the desired-force derivative used by the feedforward |
| `force_deadband_n` | 2 N | Ignores small force errors |
| `contact_threshold_n` | 3 N | When initial contact counts as established |
| `max_normal_displacement_m` | 0.12 m | Caps the accumulated TCP-normal displacement from force correction |
| `max_normal_velocity_m_s` | 0.055 m/s | Limits the rate of the TCP-normal displacement correction |
| `contact_entry_velocity_m_s` | 0.020 m/s | Restricts the approach correction speed before contact |
| `max_contact_force_n` | 150 N | Force limit that triggers emergency termination |
| `touch_force_n` | 10 N | Target normal force for the initial contact |
| `force_sync_enabled` | off | Aligns with the initial learned-force reference. The spec marks it "Optional": off until IIT answers |
| `force_sync_timeout_s` | 4 s | Maximum time for the initial force synchronisation |
| `force_sync_tolerance_n` | 2 N | Accepted force mismatch before replay begins |
| `unload_threshold_n` | 8 N | Identifies low-force conditions during unloading |
| `measured_wrench_source` | — (no default) | Where the measured wrench comes from: `grabber` (MAGICIAN Grabber) or `external` |
| `measured_wrench_topic` | Grabber: `/magician_grabber/wrench_sensed` | ROS 2 topic of the measured wrench. Required for an external source |

## Measured wrench (required capability)

The measured wrench is a *required capability*, not a dependency on one module (see
[`CONTEXT.md`](../../CONTEXT.md)): it never pulls a module into scope and is shown as a status line on
this module's tile, never as an arrow.

- **MAGICIAN Grabber:** valid only when the Grabber is in scope and delivers F/T data, i.e. tactile
  sensing is selected (Q3, which sets the Grabber's `use_ati_force`). Otherwise deployment is blocked.
- **External:** the tile asks for an external source (name it and agree the contract, as for the
  Orienteering Solver) and `measured_wrench_topic` is mandatory.
- With no valid source, or no topic for an external source, deployment is blocked. While the Grabber
  cannot be the source (e.g. grinding-only), an unanswered source counts as external.

## Outputs (written to `result.json`)

`outputs` is flat: every key of the table above (numbers as `float`, `force_sync_enabled` as a boolean).
`control_rate_hz` is the Cartesian Controller's value. `measured_wrench_topic` (a string) is written once
the source is known: the Grabber falls back to its default topic.

## Deploy blockers

`deploy_blockers` in `result.json` names the cause:

- the control rate (read from the Cartesian Controller) is not a finite number greater than 0. The value is then left out of `outputs`.

The measured wrench is not part of `result.json`: it depends on the pipeline selection and the declared external sources, which can change after Compute. The deploy step therefore evaluates it live and blocks deployment when the wrench has no valid source: the Grabber is chosen but not in scope or without tactile sensing, no source is chosen while the Grabber could provide it, an external source has no `measured_wrench_topic`, or an external source is not named.

Every other parameter has a default, so nothing else can be left incomplete.

## Notes

- Startup configuration: the grinding runtime must be restarted for changes to take effect.
- COT cannot verify the gains and force limits against the material and tool: use a validated
  material-tool recipe and do not infer gains from the material category.

## Use-case impact rules

These rules only apply while the module is in scope. They detect and explain; they never change a parameter.

- **Material (Q5):** with a selected material, a review flag: "Validated material/tool/contact-control
  configuration required. COT does not infer or tune controller gains from the selected material."

Use-case characteristics without a question yet (**nog geen vraag**): defect size / severity, geometry /
workpiece pose, robot / tool change, F/T sensor selection (beyond the measured wrench source above),
contact quality / loss and new demonstrations.

## Open points

The node name, the literal parameter names, the passing mechanism, the valid ranges of the parameters
(the spec only gives baselines) and the default of
`force_sync_enabled` are open questions for IIT; see "Open questions for IIT" in
[`COT_DMP.md`](../../docs/specs/COT_DMP.md).
