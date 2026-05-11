import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from engine.module_registry import MODULES
from engine.questionnaire_engine import compute_impacts, apply_impacts_to_modules
from models.questionnaire import QuestionnaireAnswers
from models.use_case import ConfidenceScore, ModuleState, UseCase
from storage import json_store

router = APIRouter()


class CreateUseCaseRequest(BaseModel):
    name: str


@router.post("", status_code=201)
def create_use_case(req: CreateUseCaseRequest):
    now = datetime.now(timezone.utc).isoformat()
    use_case_id = str(uuid.uuid4())[:8]

    modules = {
        mid: ModuleState(
            module_id=mid,
            module_name=info["name"],
            description=info["description"],
        )
        for mid, info in MODULES.items()
    }

    use_case = UseCase(
        id=use_case_id,
        name=req.name,
        created_at=now,
        updated_at=now,
        modules=modules,
        confidence=ConfidenceScore(score=0, percentage=0.0, level="low"),
    )
    json_store.save(use_case)
    return use_case


@router.get("")
def list_use_cases():
    return json_store.list_all()


@router.get("/{use_case_id}")
def get_use_case(use_case_id: str):
    uc = json_store.load(use_case_id)
    if not uc:
        raise HTTPException(status_code=404, detail="Use case not found")
    return uc


@router.put("/{use_case_id}/questionnaire")
def update_questionnaire(use_case_id: str, answers: QuestionnaireAnswers):
    uc = json_store.load(use_case_id)
    if not uc:
        raise HTTPException(status_code=404, detail="Use case not found")

    uc.answers = answers
    uc.updated_at = datetime.now(timezone.utc).isoformat()

    result = compute_impacts(answers)
    apply_impacts_to_modules(uc, result)

    json_store.save(uc)
    return uc


@router.delete("/{use_case_id}", status_code=204)
def delete_use_case(use_case_id: str):
    if not json_store.delete(use_case_id):
        raise HTTPException(status_code=404, detail="Use case not found")
