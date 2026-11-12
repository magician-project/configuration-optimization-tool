# Module: DMP

**ROS 2 node:** placeholder (`dmp_placeholder`) until IIT confirms the node name of the grinding runtime
**Action type:** Startup configuration (no retraining, no live tuning)

## What this module does

The DMP replays a learned grinding primitive on a detected defect. The defect class selects the
primitive: a pose profile and a wrench (force) profile, represented by radial basis functions over a
normalised phase and generated offline from demonstrations. New demonstrations mean the primitive is
regenerated and validated outside COT; COT never regenerates or retrains it. See
[`CONTEXT.md`](../../CONTEXT.md) for these terms and
[`COT_DMP.md`](../../docs/specs/COT_DMP.md) for the IIT spec.

The DMP is in scope when the pipeline selection includes grinding. It receives its ordered grinding
targets (defect class, pose, `frame_id`) per cycle from the Orienteering Solver; COT does not
configure those. The target frame is a *required capability* (see [`CONTEXT.md`](../../CONTEXT.md)):
the Localiser, which is always in scope, publishes it, and the DMP tile shows which frame that is
(the Localiser's mesh frame, default `fender`). The frames of an external defect handover must be
published by the Localiser, or the handover must state the transform to the robot planning frame.

## File overview

| File | Purpose |
|---|---|
| `compute.py` | Reads the defect classes and DMP answers → resolves the startup configuration + deploy blockers → writes `result.json` |
| `ros_interface.py` | Returns notes only: the real deploy goes through the IIT runtime, not `ros2 param set` |
| `test_compute.py` | Tests for the mapping, the blockers and the `result.json` contract |
| `README.md` | This file |

## Inputs (`module_answers["dmp"]`)

| Question key | Description |
|---|---|
| `q8_defects` (general questionnaire) | Defect classes; drives the `primitives` collection below |
| `primitives` | Collection, one row per selected Positive Dent / Negative Dent: `pose_path` and `wrench_path`. No defaults until IIT confirms the baseline artifacts. Nothing is asked for Other |
| `tool_defect_offset_x_m` / `_y_m` / `_z_m` | Tool-to-defect offset in metres. Required, no default (calibrated per tool) |

## Outputs (written to `result.json`)

`outputs` is flat (`str`, `int` or `float`). Parameters that are not configured yet are left out.

| Key | Description |
|---|---|
| `primitive_classes` | Selected classes in the DMP's labels, e.g. `"POSITIVE,NEGATIVE"` (`positive_dent` → `POSITIVE`, `negative_dent` → `NEGATIVE`) |
| `primitive_<class>_pose_path` / `primitive_<class>_wrench_path` | Paths of each selected class, e.g. `primitive_positive_dent_pose_path` |
| `tool_defect_offset_x_m` / `_y_m` / `_z_m` | Tool offset components in metres |
| `orientation_mode` | Always `"fixed"`; not a question |
| `primitive_<class>_duration_s` | Read-only: nominal replay time of the learned artifact (POSITIVE 17.717 s, NEGATIVE 17.818 s) |
| `rbf_basis_count`, `phase_samples` | Read-only: 24 and 256, fixed by the offline learner |

`primitive_class` and `defect_pose` / `frame_id` are per-cycle runtime inputs and are not configured
by COT.

## Deploy blockers

`deploy_blockers` in `result.json` names the cause of each one:

- no defect class selected;
- `other` selected: "defect class '`<description>`' has no learned grinding primitive";
- a pose or wrench path missing for a selected class;
- a tool offset component missing or not a number.

## Notes

- COT only checks that the paths are filled in, not that the files exist on the runtime.
- COT cannot verify the tool offset calibration.

## Use-case impact rules

These rules only apply while the module is in scope. They detect and explain; they never change a parameter.

- **Defect classes (Q8):** an impact "configure learned grinding primitive for: `<classes>`". A missing
  configuration and `other` are deploy blockers (see above).
- **Time constraint (Q9):** one defect cycle is estimated as `reach_duration_s + touch_dwell_s + max(baseline
  primitive duration of the selected classes) + unload_extra_duration_s + go_away_duration_s`, using the
  [Cartesian Controller](../cartesian_controller/README.md) answers (or their defaults). The baseline durations
  (NEGATIVE 17.818 s, POSITIVE 17.717 s) are "IIT baseline, not measured from configured primitive files".
  A cycle longer than the budget gives a feasibility flag; otherwise an impact states how many complete
  baseline cycles fit. That is not a prediction: the number of defects and the travel and scheduling time
  between them are not included, and there is no question for the number of defects (it is runtime input).

Use-case characteristics without a question yet (**nog geen vraag**): defect size / severity, geometry /
workpiece pose, robot / tool change, F/T sensor selection, contact quality / loss and new demonstrations.

## Open points

The node name, the literal parameter names, the offset format and the baseline primitives are open
questions for IIT; see "Open questions for IIT" in [`COT_DMP.md`](../../docs/specs/COT_DMP.md).
