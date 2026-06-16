from typing import Dict

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
            "Provides localization of entities relative to the robot in the ROS2 TF2 framework. "
            "Foundational for motion planning. Supports model-free (approach 1) and "
            "model-based localization (approaches 2 & 3, require a 3D mesh)."
        ),
        "characteristics": [
            "No time constraint (relaxed processing pipeline)",
            "Material Y (localization approach selection)",
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
}
