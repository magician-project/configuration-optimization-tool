from typing import Dict, List, Optional

# Each module: id -> {name, ros_name, description, characteristics, compute_module}
MODULES: Dict[str, dict] = {
    "grabber": {
        "name": "Grabber",
        "ros_name": "magician_grabber",
        "description": (
            "Core sensor driver. Provides software access to all physical sensors on the "
            "Sensing Robot: GiGE Camera, ATI F/T Sensor, Teensy Accelerometer, Camera Light "
            "Controller, buttons, and ToF range finders."
        ),
        "characteristics": [
            "Addition of an extra sensor modality",
            "Multiple robot arms",
            "Usage of a different GiGE camera",
            "Addition of more lights for better illumination",
        ],
        "compute_module": "modules.grabber.compute",
    },
    "orienteering_solver": {
        "name": "Orienteering Solver",
        "ros_name": "op_solver",
        "description": (
            "Generates optimal schedules for cleaning robots to address defects. "
            "Determines the sequence of defects to visit and service time to spend on each. "
            "Problem variants: OP (default), TSP, TOP (multi-arm), OPTW (time windows), OPVP (variable profit)."
        ),
        "characteristics": [
            "No time constraint → TSP",
            "Multiple robot arms → TOP",
            "Defects in timeframe → OPTW",
            "Profit definition changes → OPVP / custom profit",
            "Type of defect (profit + service time calibration)",
            "Material (profit + service time calibration)",
        ],
        "compute_module": "modules.orienteering_solver.compute",
    },
    "localiser": {
        "name": "Localiser",
        "ros_name": "localisation",
        "description": (
            "Publishes the pose of a workpiece mesh relative to the robot base in the ROS2 TF2 "
            "framework. Foundational for motion planning. A calibrated Setup is registered once "
            "(operator + robot, requires a mesh) and then republished at runtime as static or "
            "slider-corrected dynamic TF — no mesh is needed once a Setup is registered."
        ),
        "characteristics": [
            "3D mesh availability (blocks registering a new Setup)",
            "Moving fixture / conveyor (static vs dynamic broadcast mode)",
        ],
        "compute_module": "modules.localiser.compute",
    },
    "tactile_sensor": {
        "name": "Tactile Classifier",
        "ros_name": "tactile_classifier_system",
        "description": (
            "Detects and classifies surface defects using tactile probe data (force, acceleration). "
            "CNN-LSTM / LSTM-CNN ensemble model. Must be retrained whenever materials, "
            "object sizes, or defect types change."
        ),
        "characteristics": [
            "Different materials, object sizes, dirt/dent types, and time constraints → retrain ML model",
        ],
        "compute_module": "modules.tactile_sensor.compute",
    },
    "vision_classifier": {
        "name": "Vision Classifier",
        "ros_name": "magician_vision_classifier",
        "description": (
            "Visual defect detection and classification using camera images. "
            "Implicitly affected when new materials are introduced — model must be retrained "
            "and the Vision Model Name parameter in the Configuration Module must be updated."
        ),
        "characteristics": [
            "(implicit) Retrain vision model on new material data",
        ],
        "compute_module": "modules.vision_classifier.compute",
    },
    "ergodic_control": {
        "name": "Ergodic Control",
        "ros_name": "magician_ergodic_control",
        "description": (
            "Plans inspection trajectories that prioritise high-risk surface regions. "
            "Uses a Kalman filter to maintain a belief over defect distributions, "
            "combines historical data and welding process priors, then solves an ergodic "
            "control optimisation to generate end-effector waypoints on the 3D mesh."
        ),
        "characteristics": [
            "Mesh availability (trajectory planning requires a 3D surface model)",
            "Time budget (affects trajectory density and waypoint count)",
            "Material / defect context (informs prior distribution)",
        ],
        "compute_module": "modules.ergodic_control.compute",
    },
    "motion_planning": {
        "name": "Motion Planner",
        "ros_name": "motion_planner",
        "description": (
            "Converts target poses or Cartesian paths into time-sampled end-effector "
            "references. Transforms poses through TF, optionally projects paths onto "
            "workpiece meshes, assigns surface-normal orientations, applies velocity "
            "limits, and selects impedance/admittance control and sander state."
        ),
        "characteristics": [
            "Different robot/tool (reference frames, velocity limits, controller mode)",
            "Different workpiece shape/size (mesh, path, offset, approach velocity)",
            "Contact tasks (admittance force source and PI limits)",
            "Tighter time limits (path density/frequency, max_vel)",
        ],
        "compute_module": "modules.motion_planning.compute",
    },
}

# Default module set per task type. "grinding" already implies inspection — there is no
# grind-only scenario — so it's a superset of "inspection", not a separate branch.
DEFAULT_MODULES_BY_TASK_TYPE: Dict[str, List[str]] = {
    "inspection": ["grabber", "localiser", "vision_classifier", "ergodic_control"],
    "grinding": [
        "grabber", "localiser", "vision_classifier", "ergodic_control",
        "orienteering_solver", "motion_planning",
    ],
}


def compute_default_modules(task_type: Optional[str], additional_sensors: Optional[List[str]] = None) -> List[str]:
    """Pure function: default module set for a task type.

    task_type=None (not yet answered) falls back to "grinding" (the full set) for backward
    compatibility with use cases saved before this question existed. tactile_sensor is added
    only when tactile sensing was selected (Q3), regardless of task type.
    """
    base = DEFAULT_MODULES_BY_TASK_TYPE.get(task_type, DEFAULT_MODULES_BY_TASK_TYPE["grinding"])
    modules = list(base)
    if additional_sensors and "tactile" in additional_sensors:
        modules.append("tactile_sensor")
    return modules


def resolve_effective_overrides(
    module_overrides: Dict[str, bool], default_modules: List[str]
) -> Dict[str, bool]:
    """Merge explicit per-module overrides with the default module set.

    An explicit override always wins and persists regardless of task type. A
    module with no explicit override simply follows the default module set —
    active if it's in scope, disabled (hard filter) if it isn't. This is what
    makes "Reset to default" meaningful: clearing an override lets a module
    resume tracking the default set automatically, including across later
    task-type changes.
    """
    return {mid: module_overrides.get(mid, mid in default_modules) for mid in MODULES}
