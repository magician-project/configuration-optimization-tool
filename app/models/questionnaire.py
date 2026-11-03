from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, List, Dict, Any

# Canonical Q8 values. Modules map these to their own interface labels.
DEFECT_CLASSES = ("positive_dent", "negative_dent", "other")


class ObjectDimensions(BaseModel):
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    unit: str = "m"


class QuestionnaireAnswers(BaseModel):
    # Section A: Robot Configuration
    q1_robot_arms: Optional[str] = None       # "single" | "multiple"
    q1_num_arms: Optional[int] = None
    # None = not yet answered; treated as "both" (full module set) for backward compatibility.
    q_pipeline: Optional[str] = None          # "inspection" | "grinding" | "both"

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_task_type(cls, data: Any) -> Any:
        # Legacy q_task_type "grinding" meant inspection + grinding, i.e. "both".
        if isinstance(data, dict) and "q_task_type" in data and not data.get("q_pipeline"):
            data = dict(data)
            legacy = data.pop("q_task_type")
            data["q_pipeline"] = {"grinding": "both", "inspection": "inspection"}.get(legacy)
        return data

    # Section B: Sensors & Perception
    q2_camera_type: Optional[str] = None      # "standard" | "gige" | "other"
    q2_camera_spec: Optional[str] = None
    q2_camera_resolution: Optional[Dict[str, Any]] = None  # {"width": int, "height": int}
    q2_camera_framerate: Optional[float] = None
    q2_stream_shm: Optional[str] = None       # "yes" | "no"
    q2_stream_shm_name: Optional[str] = None
    q3_additional_sensors: List[str] = []     # ["tactile", "distance", "vision"]
    q4_lighting: Optional[str] = None         # "sufficient" | "additional"
    # Note: Grabber hardware config (q_grab_*) fields are stored in
    # UseCase.module_answers["grabber"], not here.

    # Section C: Material & Surface Properties
    q5_materials: List[str] = []              # ["metal", "wood", "plastic", "other"]
    q5_other_material: Optional[str] = None
    q6_object_size: Optional[str] = None      # "small" | "large" | "variable"
    q6_dimensions: Optional[ObjectDimensions] = None
    q7_mesh: Optional[str] = None             # "available" | "in_preparation" | "not_available"
    q7_mesh_status: Optional[str] = None      # "cad" | "scanning" | "unknown"

    # Section D: Defect Detection
    q8_defects: List[str] = []               # defect classes: values of DEFECT_CLASSES
    q8_other_defect: Optional[str] = None    # description, required when "other" is selected

    @field_validator("q8_defects", mode="before")
    @classmethod
    def _drop_old_defect_types(cls, value: Any) -> Any:
        # The old values (dents, dirt, surface_damage) have no safe mapping to a
        # defect class, so they are dropped and Q8 must be answered again.
        if isinstance(value, list):
            return [v for v in value if v in DEFECT_CLASSES]
        return value
    # Note: Vision Classifier config (q_clf_*) fields are now stored in
    # UseCase.module_answers["vision_classifier"], not here.

    # Section E: Time & Priority Constraints
    q9_time: Optional[str] = None             # "none" | "tight"
    q9_time_value: Optional[float] = None
    q9_time_unit: Optional[str] = "minutes"   # "seconds" | "minutes" | "hours"
    q10_profit: Optional[str] = None          # "standard" | "custom"
    # Note: Ergodic Control config (q_ergodic_*) fields are stored in
    # UseCase.module_answers["ergodic_control"], not here.
