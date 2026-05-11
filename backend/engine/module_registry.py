from typing import Dict

# Each module: id -> {name, ros_name, description, characteristics}
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
    },
}
