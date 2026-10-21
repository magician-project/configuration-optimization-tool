from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import unquote, urlsplit

REPO_ROOT = Path(__file__).resolve().parents[2]

README_EMPTY_STATE = "No documentation available for this module."

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

PIPELINES = ("inspection", "grinding", "both")

# Localiser and Motion Planner are shared: in scope for every pipeline until a question drives them.
_SHARED_MODULES = ["localiser", "motion_planning"]
_INSPECTION_MODULES = ["grabber", "vision_classifier", "ergodic_control"]
_GRINDING_MODULES = ["orienteering_solver"]

DEFAULT_MODULES_BY_PIPELINE: Dict[str, List[str]] = {
    "inspection": _INSPECTION_MODULES + _SHARED_MODULES,
    "grinding": _GRINDING_MODULES + _SHARED_MODULES,
    "both": _INSPECTION_MODULES + _GRINDING_MODULES + _SHARED_MODULES,
}


def is_assessed(pipeline: Optional[str]) -> bool:
    """False while the pipeline selection is unanswered: scope cannot be derived yet."""
    return pipeline in PIPELINES


def normalize_pipeline(pipeline: Optional[str]) -> str:
    """Unanswered or unknown pipeline falls back to "both" (the full set)."""
    return pipeline if pipeline in PIPELINES else "both"


def module_readme_path(module_id: str, root: Path = REPO_ROOT) -> Optional[Path]:
    """README location derived from compute_module (modules.grabber.compute -> modules/grabber/README.md)."""
    module = MODULES.get(module_id)
    if module is None:
        return None
    package = module["compute_module"].rsplit(".", 1)[0]
    return root.joinpath(*package.split("."), "README.md")


def load_module_readme(module_id: str, root: Path = REPO_ROOT) -> str:
    """README markdown for a module, or README_EMPTY_STATE if missing or unreadable."""
    path = module_readme_path(module_id, root)
    if path is None:
        return README_EMPTY_STATE
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return README_EMPTY_STATE


def resolve_readme_link(module_id: str, href: str, root: Path = REPO_ROOT) -> Optional[Path]:
    """Existing file inside the repo that a relative README link points to, else None."""
    readme = module_readme_path(module_id, root)
    parts = urlsplit(href)
    if readme is None or parts.scheme or parts.netloc or not parts.path:
        return None
    target = (readme.parent / unquote(parts.path)).resolve()
    if not target.is_file() or not target.is_relative_to(root.resolve()):
        return None
    return target


def compute_default_modules(pipeline: Optional[str], additional_sensors: Optional[List[str]] = None) -> List[str]:
    """Pure function: default module set for a pipeline selection.

    tactile_sensor is added only when tactile sensing was selected (Q3) and the pipeline
    includes inspection.
    """
    pipeline = normalize_pipeline(pipeline)
    modules = list(DEFAULT_MODULES_BY_PIPELINE[pipeline])
    if pipeline != "grinding" and additional_sensors and "tactile" in additional_sensors:
        modules.append("tactile_sensor")
    return modules
