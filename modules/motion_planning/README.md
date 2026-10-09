# Module: Motion Planner

**ROS 2 node:** `/motion_planner`
**Action type:** Reconfiguration (no retraining required)

## What this module does

The Motion Planner converts target poses or Cartesian paths into time-sampled
end-effector references, per the partner-provided configuration spec. It
transforms poses through TF, optionally projects paths onto workpiece meshes,
assigns surface-normal orientations, applies velocity limits, and queues the
resulting motions. It can also select impedance/admittance control and
operate the sander.

COT's job is to configure the **node parameters** (reference frames,
admittance tuning, force-sensor topics, impedance sensor selection, debug
flags) via live `ros2 param set` commands. The planner's motion services
(`reach_position`, `execute_trajectory`, etc.) take per-call arguments such
as `control_mode`, `sander`, mesh, offset, and velocity — those are not
configured here; they are supplied by whichever module or operator issues
the request (see the interface reference below).

## File overview

| File | Purpose |
|---|---|
| `compute.py` | Reads questionnaire answers → resolves section-4 node params → writes `result.json` |
| `generate_config.py` | Writes `motion_planner_params.yaml`, the ROS 2 parameter file the node reads |
| `ros_interface.py` | Translates `result.json` outputs into `ROS2Command` objects (live `param` sets + operator-facing notes) |
| `README.md` | This file |

## Inputs (`module_answers["motion_planning"]`)

All fields map 1:1 to the partner's "COT configuration parameters" table.

| Question key | Default | Description |
|---|---|---|
| `q_mp_base_link` | `"base_link"` | Robot reference frame |
| `q_mp_ee_link` | `"tcp"` | Controlled end-effector frame |
| `q_mp_integration_dt` | `0.001` | Planner/output sampling period (s) |
| `q_mp_ft_link` | `ee_link` | Force/torque sensor frame; defaults to `ee_link` |
| `q_mp_proportional_gain` | `1/3600` | Z-admittance proportional gain |
| `q_mp_integral_gain` | `4.6` | Z-admittance integral gain |
| `q_mp_integral_bound` | `0.02` | Maximum integral displacement (m) |
| `q_mp_integral_velocity_bound` | `0.01` | Maximum integral correction rate (m/s) |
| `q_mp_mini58_topic` | `"/ati_ft_sensor/wrench_sensed"` | Force sensor input |
| `q_mp_nano17_topic` | `"/magician_grabber/wrench_sensed"` | Force sensor input |
| `q_mp_impedance_sensor` | `"force_estimate"` | Force source: `force_estimate`, `mini58`, or `nano17` |
| `q_mp_debug_prints` | `"no"` | Diagnostic logging |
| `q_mp_debug_lib` | `"no"` | Diagnostic logging |

## Interface reference

All services are under `/motion_planner`; unless noted, the response is
`bool success` (request accepted/queued, not physical completion). These
services are **not** configured by this module — they take per-call
arguments (`control_mode`, `sander`, mesh, offset, velocity) supplied by
whichever module or operator issues the request.

| Service | Essential interface |
|---|---|
| `reach_position` | `desired_pos`, `max_vel`, `immediate_execution`, `control_mode` |
| `mesh_reach_position` | `mesh`, `desired_pos`, `offset`, `max_vel`, `control_mode`, `sander` |
| `execute_ptp_motion` | `y0`, `g`, `max_vel`, `plan_y0_motion`, `control_mode`, `sander` |
| `execute_mesh_ptp_motion` | `mesh`, `y0`, `g`, `offset`, `max_vel`, `plan_y0_motion`, `approach_vel`, `control_mode`, `sander` |
| `execute_trajectory` | `frame_link`, `path`, `plan_y0_motion`, `approach_vel`, `control_mode`, `sander` |
| `execute_trajectory_on_mesh` | `mesh`, `frame_link`, `path`, `path_freq_hz`, `offset`, `plan_y0_motion`, `approach_vel`, `control_mode`, `sander` |
| `hold_position` / `move_relative` / `discrete_dmp` / `rhytmic_dmp` | see partner spec |
| `project_poses_to_mesh` | `poses`, `mesh_links` → projected `poses[]`, `success[]` |
| `ptp_time_estimate` | `poses` → `Float64MultiArray` transition times |
| `set_broadcast_state` | `std_srvs/srv/SetBool` |
| `safe_stop` | `std_srvs/srv/Trigger` |

Outputs: `/cartesian/<ee_link>/reference` (`PoseStamped`), `/motion_planner/planned_path` (`nav_msgs/Path`, transient-local).

`execute_trajectory_on_mesh` already has a consumer in this codebase —
`modules/ergodic_control` calls it with the trajectories it plans; this
module only configures the planner node itself, it does not issue those
calls. If a future module needs per-call defaults (e.g. a default mesh or
velocity), add the corresponding `q_mp_*` fields and a real consumer at
that point rather than speculatively ahead of time.

## Outputs (written to `result.json`)

| Key | Type | Description |
|---|---|---|
| `base_link`, `ee_link`, `ft_link` | `str` | TF frame names |
| `integration_dt` | `float` | Sampling period (s) |
| `integration_dt_rename_pending` | `bool` | Always `True` — see caveat below |
| `proportional_gain`, `integral_gain`, `integral_bound`, `integral_velocity_bound` | `float` | Z-admittance tuning |
| `mini58_topic`, `nano17_topic` | `str` | Force sensor topics |
| `impedance_sensor` | `str` | `force_estimate` \| `mini58` \| `nano17` |
| `debug_prints`, `debug_lib` | `bool` | Diagnostic logging flags |

## ROS 2 commands fired

### Parameter settings (via `ros2 param set` on `/motion_planner`)

- `base_link`, `ee_link`, `ft_link`
- `integration_dt`
- `proportional_gain`, `integral_gain`, `integral_bound`, `integral_velocity_bound`
- `mini58_topic`, `nano17_topic`, `impedance_sensor`
- `debug_prints`, `debug_lib`

The partner spec does not document these as startup-only/read-only, so they
are fired as live parameter sets, consistent with the contract in
[`modules/README.md`](../README.md). `ROS_MOCK=true` (the default) logs these
commands instead of executing them.

### Notes (metadata, no command fired)

- `params_yaml_path` — generated artifact location
- `integration_dt_rename_caveat` — always; `motion_planner_params.yaml` already
  uses the correct `integration_dt` key, but warns that an external/legacy
  params file may still use the outdated `integration_timestep` name, which
  the node would silently ignore
- `force_sensor_topic_reminder` — only when `impedance_sensor` is `mini58` or
  `nano17`; prompts verifying the topic against the Grabber's wiring

## How to contribute

1. **Edit `compute.py`** — modify `run(answers)` to refine defaults or add
   new fields. Return a flat `dict` of `str | int | float | bool`.
2. **Edit `generate_config.py`** — add new keys to `motion_planner_params.yaml`
   as the node's real parameter set grows.
3. **Edit `ros_interface.py`** — add `ROS2Command` entries for new output
   keys; once the partner ships a reload service, replace the relevant
   `note` with a `service` command.
4. Test by running:
   ```
   python -m modules.motion_planning.compute <path/to/use_case.json> <output_dir>
   ```

> All values passed to ROS 2 must be `str`, `int`, `float`, or `bool`.
