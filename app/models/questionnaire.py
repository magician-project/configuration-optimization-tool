from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ObjectDimensions(BaseModel):
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    unit: str = "m"


class QuestionnaireAnswers(BaseModel):
    # Section A: Robot Configuration
    q1_robot_arms: Optional[str] = None       # "single" | "multiple"
    q1_num_arms: Optional[int] = None

    # Section B: Sensors & Perception
    q2_camera_type: Optional[str] = None      # "standard" | "gige" | "other"
    q2_camera_spec: Optional[str] = None
    q2_camera_resolution: Optional[Dict[str, Any]] = None  # {"width": int, "height": int}
    q2_camera_framerate: Optional[float] = None
    q2_camera_exposure: Optional[int] = None
    q2_camera_gain: Optional[float] = None
    q2_camera_blacklevel: Optional[float] = None
    q2_stream_shm: Optional[str] = None       # "yes" | "no"
    q2_stream_shm_name: Optional[str] = None
    q3_additional_sensors: List[str] = []     # ["tactile", "distance", "vision"]
    q3_force_sensor_ip: Optional[str] = None
    q3_force_sensor_port: Optional[int] = None
    q3_arduino_path: Optional[str] = None
    q3_teensy_path: Optional[str] = None
    q3_lighting_mode: Optional[str] = None    # "none" | "rlight" | "dlight" | "tlight" | "trigger"
    q3_tactile_stream: Optional[str] = None
    q4_lighting: Optional[str] = None         # "sufficient" | "additional"

    # Section C: Material & Surface Properties
    q5_materials: List[str] = []              # ["metal", "wood", "plastic", "other"]
    q5_other_material: Optional[str] = None
    q6_object_size: Optional[str] = None      # "small" | "large" | "variable"
    q6_dimensions: Optional[ObjectDimensions] = None
    q7_mesh: Optional[str] = None             # "available" | "in_preparation" | "not_available"
    q7_mesh_status: Optional[str] = None      # "cad" | "scanning" | "unknown"

    # Section D: Defect Detection
    q8_defects: List[str] = []               # ["dents", "dirt", "surface_damage"]

    # Section D: Magician Vision Classifier configuration
    q_clf_model: Optional[str] = None         # backbone: "resnet18" | "resnext50" | ...
    q_clf_tile_size: Optional[str] = None     # "32" | "48" | "64" | "128"
    q_clf_step_size: Optional[int] = None
    q_clf_threshold: Optional[float] = None
    q_clf_fps: Optional[float] = None
    q_clf_majority_voting: Optional[str] = None  # "yes" | "no"
    q_clf_two_stage: Optional[str] = None        # "yes" | "no"
    q_clf_model_path: Optional[str] = None
    q_clf_dataset_dir: Optional[str] = None
    q_clf_epochs: Optional[int] = None
    q_clf_batch_size: Optional[int] = None
    q_clf_learning_rate: Optional[float] = None
    q_clf_loss: Optional[str] = None             # "focal" | "cross_entropy"
    q_clf_use_lasers: Optional[str] = None       # "yes" | "no"
    q_clf_laser_topic_1: Optional[str] = None
    q_clf_laser_topic_2: Optional[str] = None
    q_clf_laser_topic_3: Optional[str] = None
    q_clf_laser_px1_x: Optional[float] = None
    q_clf_laser_px1_y: Optional[float] = None
    q_clf_laser_px2_x: Optional[float] = None
    q_clf_laser_px2_y: Optional[float] = None
    q_clf_laser_px3_x: Optional[float] = None
    q_clf_laser_px3_y: Optional[float] = None
    q_clf_laser_idw_power: Optional[float] = None
    q_clf_advanced: Optional[str] = None         # "yes" | "no"
    q_clf_aolp: Optional[str] = None             # "yes" | "no"
    q_clf_dolp: Optional[str] = None             # "yes" | "no"
    q_clf_unpolarized: Optional[str] = None      # "yes" | "no"

    # Section E: Time & Priority Constraints
    q9_time: Optional[str] = None             # "none" | "tight"
    q9_time_value: Optional[float] = None
    q9_time_unit: Optional[str] = "minutes"   # "seconds" | "minutes" | "hours"
    q10_profit: Optional[str] = None          # "standard" | "custom"
