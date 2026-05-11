from pydantic import BaseModel
from typing import Optional, List


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
    q3_additional_sensors: List[str] = []     # ["tactile", "vision"]
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

    # Section E: Time & Priority Constraints
    q9_time: Optional[str] = None             # "none" | "tight"
    q9_time_value: Optional[float] = None
    q9_time_unit: Optional[str] = "minutes"   # "seconds" | "minutes" | "hours"
    q10_profit: Optional[str] = None          # "standard" | "custom"
