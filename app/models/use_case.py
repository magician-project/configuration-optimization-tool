from __future__ import annotations

from pydantic import BaseModel
from typing import List, Optional, Dict
from app.models.questionnaire import QuestionnaireAnswers


class ModuleImpact(BaseModel):
    characteristic: str
    affects: str
    what_changes: str
    action_type: str   # "retrain" | "reconfigure" | "review"
    reason: str        # which question triggered this


class Flag(BaseModel):
    id: str
    type: str          # "error" | "warning" | "human_oversight"
    message: str
    module_id: str
    acknowledged: bool = False


class ComputeResult(BaseModel):
    """Output produced by a module's compute.py script."""
    module_id: str
    success: bool
    outputs: Dict[str, object] = {}   # str/int/float values only at leaf nodes
    error: Optional[str] = None


class ROS2Command(BaseModel):
    """A single ROS 2 command to fire (param set or service call)."""
    type: str                          # "param" | "service"
    # param set
    node: Optional[str] = None
    param_name: Optional[str] = None
    value: Optional[object] = None    # str | int | float only
    # service call
    service: Optional[str] = None
    service_type: Optional[str] = None
    request_args: Optional[Dict[str, object]] = None  # leaf values: str/int/float


class ModuleState(BaseModel):
    module_id: str
    module_name: str
    description: str
    # Full lifecycle:
    # ok -> needs_action -> validated -> computing -> computed -> deploying -> deployed
    # Error branches: compute_failed, deploy_failed
    status: str = "ok"
    impacts: List[ModuleImpact] = []
    flags: List[Flag] = []
    compute_result: Optional[ComputeResult] = None
    validated_at: Optional[str] = None
    computed_at: Optional[str] = None
    deployed_at: Optional[str] = None


class ConfidenceScore(BaseModel):
    score: int
    max: int = 7
    percentage: float
    level: str         # "low" | "medium" | "high"


class UseCase(BaseModel):
    id: str
    name: str
    created_at: str
    updated_at: str
    answers: QuestionnaireAnswers = QuestionnaireAnswers()
    modules: Dict[str, ModuleState] = {}
    confidence: ConfidenceScore = ConfidenceScore(score=0, percentage=0.0, level="low")
