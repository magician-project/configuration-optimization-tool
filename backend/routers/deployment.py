from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from engine.ros_adapter import get_adapter
from storage import json_store

router = APIRouter()


@router.post("/{use_case_id}/deploy")
def deploy(use_case_id: str):
    uc = json_store.load(use_case_id)
    if not uc:
        raise HTTPException(status_code=404, detail="Use case not found")

    # All modules with impacts must be validated before deployment
    blocking = [
        mid for mid, m in uc.modules.items()
        if m.status == "needs_action"
    ]
    if blocking:
        raise HTTPException(
            status_code=422,
            detail=f"The following module(s) must be validated before deployment: {', '.join(blocking)}",
        )

    adapter = get_adapter()
    results = {}

    for mid, module in uc.modules.items():
        if module.status != "validated":
            # ok / already deployed modules are skipped
            continue

        ros_result = adapter.deploy_module(mid, [i.model_dump() for i in module.impacts])
        if ros_result.get("success"):
            module.status = "deployed"
            module.deployed_at = datetime.now(timezone.utc).isoformat()
        else:
            module.status = "deploy_failed"
        results[mid] = ros_result

    json_store.save(uc)
    return {"use_case_id": use_case_id, "deployed": list(results.keys()), "results": results}
