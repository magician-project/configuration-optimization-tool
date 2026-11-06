# Module: Impedance Controller

**ROS 2 node:** placeholder (`impedance_controller_placeholder`) until IIT confirms the node name of the grinding runtime
**Action type:** Startup configuration (no retraining, no live tuning)

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

All parameters are optional: an unanswered one takes the spec default.

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

The measured wrench topic and the wrench source are not configured here; they fall under the required
capabilities work (ticket 12).

## Outputs (written to `result.json`)

`outputs` is flat: every key of the table above (numbers as `float`, `force_sync_enabled` as a boolean).
`control_rate_hz` is the Cartesian Controller's value.

## Deploy blockers

None: every parameter has a default.

## Notes

- Startup configuration: the grinding runtime must be restarted for changes to take effect.
- COT cannot verify the gains and force limits against the material and tool: use a validated
  material-tool recipe and do not infer gains from the material category.

## Open points

The node name, the literal parameter names, the passing mechanism and the default of
`force_sync_enabled` are open questions for IIT; see "Open questions for IIT" in
[`COT_DMP.md`](../../docs/specs/COT_DMP.md).
