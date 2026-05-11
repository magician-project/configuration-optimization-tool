from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from storage import json_store

router = APIRouter()


@router.get("/{use_case_id}/modules")
def get_modules(use_case_id: str):
    uc = json_store.load(use_case_id)
    if not uc:
        raise HTTPException(status_code=404, detail="Use case not found")
    return list(uc.modules.values())


@router.get("/{use_case_id}/modules/{module_id}")
def get_module(use_case_id: str, module_id: str):
    uc = json_store.load(use_case_id)
    if not uc:
        raise HTTPException(status_code=404, detail="Use case not found")
    module = uc.modules.get(module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    return module


@router.post("/{use_case_id}/modules/{module_id}/acknowledge-flags")
def acknowledge_flags(use_case_id: str, module_id: str):
    uc = json_store.load(use_case_id)
    if not uc:
        raise HTTPException(status_code=404, detail="Use case not found")
    module = uc.modules.get(module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    for flag in module.flags:
        flag.acknowledged = True

    json_store.save(uc)
    return module


@router.post("/{use_case_id}/modules/{module_id}/validate")
def validate_module(use_case_id: str, module_id: str):
    uc = json_store.load(use_case_id)
    if not uc:
        raise HTTPException(status_code=404, detail="Use case not found")
    module = uc.modules.get(module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    if module.status == "ok":
        raise HTTPException(
            status_code=422,
            detail="Module has no required actions — nothing to validate.",
        )

    unacked = [f for f in module.flags if not f.acknowledged]
    if unacked:
        msgs = "; ".join(f.message for f in unacked)
        raise HTTPException(
            status_code=422,
            detail=f"{len(unacked)} flag(s) must be acknowledged before validation: {msgs}",
        )

    module.status = "validated"
    module.validated_at = datetime.now(timezone.utc).isoformat()
    json_store.save(uc)
    return module
