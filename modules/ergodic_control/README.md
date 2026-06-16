# Module: Ergodic Control

**ROS 2 node:** `/magician_ergodic_control`, `/magician_configuration`  
**Dependencies:** Vision Classifier (defects), Grabber (end-effector poses), Motion Planner (trajectory execution)  
**Type:** Trajectory Planning + State Estimation (Kalman Filter)

## What this module does

The Ergodic Control module plans inspection trajectories that prioritize informative regions of a surface. It uses:

1. **Historical data** from previous inspections (defect locations)
2. **Welding process data** (spatter-prone areas) from the PLC
3. **Kalman filter** to maintain a belief about defect spatial distribution
4. **Ergodic control** to generate a trajectory whose time-averaged statistics match the target probability distribution

This ensures the robot spends more time inspecting high-risk areas, improving defect detection efficiency.

## File overview

| File | Purpose |
|---|---|
| `compute.py` | Reads questionnaire → validates mesh availability → outputs trajectory parameters |
| `ros_interface.py` | Translates `result.json` outputs into `ROS2Command` objects (parameter sets, service calls) |
| `generate_config.py` | Writes `trajectory_config.json` and `kalman_config.json` for runtime use |
| `ergodic_control.py` | **Algorithm module** — contains Kalman filter + PDF computation + ergodic optimization stubs |
| `README.md` | This file |

## Inputs (from questionnaire)

| Question key | Description |
|---|---|
| `q_ergodic_mesh_path` | Path to `.stl` mesh file (required if mesh available) |
| `q_ergodic_mesh_available` | "yes" \| "no" \| "in_preparation" |
| `q_ergodic_time_budget` | Inspection time budget in seconds (default: 60) |
| `q_ergodic_sensor_offset` | Camera standoff distance in meters (default: 0.05 m) |
| `q_ergodic_use_welding_priors` | "yes" \| "no" — use PLC welding data as prior (default: "yes") |
| `q_ergodic_use_historical` | "yes" \| "no" — use previous car inspection data (default: "yes") |
| `q_ergodic_pdf_resolution` | Grid resolution for PDF computation: 16, 32, 64, 128 (default: 32) |
| `q_ergodic_kalman_process_noise` | Kalman filter process noise σ² (default: 0.1) |
| `q_ergodic_kalman_measurement_noise` | Kalman filter measurement noise σ² (default: 0.5) |
| `q_ergodic_trajectory_density` | "sparse" \| "normal" \| "dense" — waypoint density (default: "normal") |

### Additional Dependencies

The module also uses:
- `q2_stream_shm_name` — Shared memory stream name for camera data
- `q2_camera_framerate` — Camera FPS (affects Kalman filter update rate)
- `q5_materials` — Target material types (for context)
- `q8_defects` — Expected defect types (for context)

## Outputs (written to `result.json`)

| Key | Type | Description |
|---|---|---|
| `mesh_path` | `str` | Path to mesh file (empty if unavailable) |
| `mesh_available` | `str` | "yes" \| "no" \| "in_preparation" |
| `sensor_offset_m` | `float` | Camera standoff distance |
| `time_budget_seconds` | `float` | Inspection time budget |
| `trajectory_density` | `str` | Waypoint density: "sparse" \| "normal" \| "dense" |
| `estimated_trajectory_points` | `int` | Estimated number of trajectory waypoints |
| `use_historical_data` | `bool` | Whether historical defect data is used |
| `use_welding_priors` | `bool` | Whether welding priors are used |
| `pdf_grid_resolution` | `int` | PDF computation resolution |
| `kalman_process_noise` | `float` | Kalman process noise σ² |
| `kalman_measurement_noise` | `float` | Kalman measurement noise σ² |
| `target_materials` | `str` | Comma-separated list of materials |
| `defect_types` | `str` | Comma-separated list of defect types |
| `stream_name` | `str` | Shared memory stream name |

## ROS 2 Commands Fired

### Parameter Settings (via `ros2 param set`)

On `/magician_ergodic_control`:
- `mesh_file_path` — Path to .stl mesh
- `target_materials` — Material types
- `defect_types` — Defect types
- `camera_stream_name` — Shared memory stream for camera

On `/magician_configuration`:
- `ergodic_control_enabled` — Boolean flag

### Service Calls (runtime tunable)

`/magician_ergodic_control/<service_name>`:
- `set_sensor_offset` (float) — Camera standoff distance
- `set_time_budget` (float) — Inspection time budget
- `set_trajectory_density` (string) — Waypoint density
- `set_pdf_resolution` (int) — PDF grid resolution
- `set_use_historical_data` (bool) — Enable historical data
- `set_use_welding_priors` (bool) — Enable welding priors
- `set_process_noise` (float) — Kalman process noise
- `set_measurement_noise` (float) — Kalman measurement noise

### Notes (metadata)

- `trajectory_config_path` — Path to generated `trajectory_config.json`
- `kalman_config_path` — Path to generated `kalman_config.json`

## Algorithm Overview

### 1. State Belief Update (Kalman Filter)

**Input**: Defections from vision classifier, background probability, end-effector poses  
**Process**: Extended Kalman Filter (EKF) to estimate spatial distribution of defects

- **Prediction step**: Use motion model (assume correlated defects across lines)
- **Measurement update**: Transform camera-frame detections to mesh frame using end-effector poses
- **Background fusion**: Negative measurements (background probability) reduce uncertainty in unexplored areas

**Output**: State covariance matrix + mean belief about defect locations

### 2. Target PDF Computation

**Input**: State belief from Kalman filter, welding priors (optional)  
**Process**: Construct 2D probability density function on mesh surface

- Place Gaussian kernels at historical defect locations (weight by confidence)
- Add welding spatter prior (high probability in weld seams)
- Subtract explored regions (visited by previous trajectory)
- Normalize to probability distribution

**Output**: 2D target PDF on regular grid

### 3. Ergodic Trajectory Optimization

**Input**: Target PDF, time budget, mesh bounds  
**Process**: Solve ergodic control optimization problem

- Minimize: KL divergence between trajectory time-statistics and target PDF
- Constraints: time budget, dynamics (velocity/acceleration), collision avoidance
- Discretize trajectory into waypoints based on `trajectory_density`

**Output**: 2D trajectory (x, y coordinates in mesh frame)

### 4. 3D Projection

**Input**: 2D trajectory, mesh file, sensor offset  
**Process**: Project to 3D and apply offset

- For each 2D point: find closest point on mesh surface
- Apply sensor offset (normal to surface × offset distance)
- Compute end-effector orientation (approaching normal, or user-defined)

**Output**: 3D end-effector poses (x, y, z, quaternion)

## How to Implement the Algorithm

The skeleton is in `ergodic_control.py` with these TODO sections:

### 1. Mesh Loading (load_mesh)

```python
# Requires: trimesh library (pip install trimesh)
import trimesh

mesh = trimesh.load(self.mesh_path)
bounds = mesh.bounds  # [[x_min, y_min, z_min], [x_max, y_max, z_max]]
```

### 2. Kalman Filter (update_state_belief)

```python
# Prediction step: (No motion model needed; assume defect locations are static)
# Measurement update: 
#   1. Transform detections from camera frame to mesh frame using end-effector poses
#   2. Run EKF update with measurement covariance = 1 / detection probability
#   3. Run negative update for background_prob in unexplored regions
```

### 3. PDF Computation (compute_target_pdf)

```python
# For each historical defect:
#   pdf += gaussian_2d(x, y, mean=(defect_x, defect_y), sigma=0.1) * defect_confidence
# 
# If welding_priors available:
#   pdf += 0.5 * welding_priors  # Weight down (lower than defects)
#
# Normalize: pdf /= pdf.sum()
```

### 4. Ergodic Optimization (compute_ergodic_trajectory)

Typical approach: Fourier basis representation

```python
# Trajectory x(t), y(t) represented as Fourier series:
#   x(t) = sum_k (a_k * cos(2π k t) + b_k * sin(2π k t))
#   y(t) = similar
#
# For each harmonic mode k, ergodicity requires:
#   Σ_time [x_k(t)]² / T ≈ ∫ target_pdf(x,y) x² dx dy
#
# Solve via gradient descent on coefficients {a_k, b_k}
```

### 5. 3D Projection (project_to_3d_mesh)

```python
# For each 2D point (x, y):
#   Find closest point on mesh surface
#   Compute surface normal at that point
#   Apply offset: z = mesh_z + sensor_offset * normal_z
#   Compute orientation: approach along normal
```

## How to contribute

1. **Implement algorithm** in `ergodic_control.py`:
   - Replace TODO stubs with actual Kalman filter, PDF, and optimization code
   - Use libraries: `trimesh` (mesh), `numpy/scipy` (math), `scipy.optimize` (ergodic optimization)

2. **Test with a use case**:
   ```bash
   python -m modules.ergodic_control.compute data/use_cases/c8d9cc02/use_case.json data/use_cases/c8d9cc02/compute_outputs/ergodic_control
   ```

3. **Verify outputs**:
   - Check `trajectory_config.json` and `kalman_config.json` are valid JSON
   - Check `result.json` has `success: true` and all expected fields
   - Verify trajectory waypoints are within mesh bounds and respect sensor offset

4. **Integration**:
   - Once working, the `ComputeRunner` will call this automatically for each use case
   - ROS commands will be generated and queued for motion planner execution

## Notes

- **Mesh requirement**: If mesh is unavailable, module will still generate a trajectory (assumes flat surface)
- **Historical data**: Module degrades gracefully if no previous inspection data exists (uses welding priors only)
- **Kalman filter**: Process and measurement noise can be tuned per use case via questionnaire
- **Performance**: For large meshes and high PDF resolution, computation may take seconds; optimize with spatial indexing if needed

> All values passed to ROS 2 must be `str`, `int`, or `float`.
