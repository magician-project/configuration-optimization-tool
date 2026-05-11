from pydantic import BaseModel
from typing import List, Optional, Dict
from models.questionnaire import QuestionnaireAnswers


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


class ModuleState(BaseModel):
    module_id: str
    module_name: str
    description: str
    status: str = "ok"  # "ok" | "needs_action" | "validated" | "deployed" | "deploy_failed"
    impacts: List[ModuleImpact] = []
    flags: List[Flag] = []
    validated_at: Optional[str] = None
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
