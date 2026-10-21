"""
JSON persistence — one folder per use case:

    data/use_cases/{id}/
        use_case.json
        compute_outputs/
            {module_id}/
                result.json
"""

import json
import os
import logging
from typing import Optional, List
from app.models.use_case import UseCase, ComputeResult

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "use_cases")


def _ensure_dir() -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)


def _safe_id(use_case_id: str) -> str:
    return "".join(c for c in use_case_id if c.isalnum() or c == "-")


def _use_case_dir(use_case_id: str) -> str:
    return os.path.join(_DATA_DIR, _safe_id(use_case_id))


def _use_case_path(use_case_id: str) -> str:
    return os.path.join(_use_case_dir(use_case_id), "use_case.json")


def _compute_output_path(use_case_id: str, module_id: str) -> str:
    safe_module = "".join(c for c in module_id if c.isalnum() or c in "-_")
    return os.path.join(_use_case_dir(use_case_id), "compute_outputs", safe_module, "result.json")


# ---------------------------------------------------------------------------
# Use case CRUD
# ---------------------------------------------------------------------------

def save(use_case: UseCase) -> None:
    folder = _use_case_dir(use_case.id)
    os.makedirs(folder, exist_ok=True)
    with open(_use_case_path(use_case.id), "w", encoding="utf-8") as f:
        json.dump(use_case.model_dump(), f, indent=2)


def load(use_case_id: str) -> Optional[UseCase]:
    path = _use_case_path(use_case_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        uc = UseCase(**data)
        _ensure_all_modules(uc)
        return uc
    except Exception:
        logger.exception("Failed to load use case: %s", use_case_id)
        return None


def _ensure_all_modules(uc: UseCase) -> None:
    """Add any modules that exist in the registry but are missing from the stored use case.
    This handles the case where new modules are added after a use case was first saved."""
    from app.engine.module_registry import MODULES, compute_default_modules, is_assessed
    from app.engine.questionnaire_engine import sync_external_input_status
    from app.models.use_case import ModuleState
    for mid, info in MODULES.items():
        if mid not in uc.modules:
            uc.modules[mid] = ModuleState(
                module_id=mid,
                module_name=info["name"],
                description=info["description"],
                status="not_assessed",  # _reconcile_scope derives the real status
            )
    # Always recomputed on load — use cases saved before this field existed (or not
    # re-saved since) would otherwise be stuck with the Pydantic default `[]`.
    # An unanswered pipeline stays [] (see is_assessed).
    uc.default_modules = (
        compute_default_modules(uc.answers.q_pipeline, uc.answers.q3_additional_sensors)
        if is_assessed(uc.answers.q_pipeline) else []
    )
    _reconcile_scope(uc)
    sync_external_input_status(uc)


def _reconcile_scope(uc: UseCase) -> None:
    """Align stored module status with the derived scope, touching only modules whose scope changed.

    Covers use cases saved before scope was derived from the pipeline selection (including the
    old "disabled" status), without resetting the lifecycle of unaffected modules.
    """
    from app.engine.module_registry import MODULES, is_assessed
    from app.engine.questionnaire_engine import compute_impacts
    from app.models.use_case import Flag, ModuleImpact

    if not is_assessed(uc.answers.q_pipeline):
        for mid, ms in uc.modules.items():
            if mid in MODULES and ms.status in ("ok", "needs_action", "disabled", "out_of_scope"):
                ms.status, ms.impacts, ms.flags = "not_assessed", [], []
        return

    impacts_by_module = None
    for mid, ms in uc.modules.items():
        if mid not in MODULES:
            continue
        if mid not in uc.default_modules:
            if ms.status != "out_of_scope":
                ms.status, ms.impacts, ms.flags = "out_of_scope", [], []
        elif ms.status in ("disabled", "out_of_scope", "not_assessed"):
            if impacts_by_module is None:
                impacts_by_module = compute_impacts(uc.answers, uc.module_answers)["module_impacts"]
            data = impacts_by_module[mid]
            ms.impacts = [ModuleImpact(**i) for i in data["impacts"]]
            ms.flags = [Flag(**f) for f in data["flags"]]
            ms.status = "needs_action" if ms.impacts else "ok"


def list_all() -> List[UseCase]:
    _ensure_dir()
    use_cases: List[UseCase] = []
    for entry in os.scandir(_DATA_DIR):
        if not entry.is_dir():
            continue
        uc_path = os.path.join(entry.path, "use_case.json")
        if not os.path.exists(uc_path):
            continue
        try:
            with open(uc_path, encoding="utf-8") as f:
                data = json.load(f)
            uc = UseCase(**data)
            _ensure_all_modules(uc)
            use_cases.append(uc)
        except Exception:
            logger.exception("Failed to load use case in folder: %s", entry.name)
    return sorted(use_cases, key=lambda u: u.created_at, reverse=True)


def delete(use_case_id: str) -> bool:
    folder = _use_case_dir(use_case_id)
    if not os.path.isdir(folder):
        return False
    import shutil
    shutil.rmtree(folder)
    return True


# ---------------------------------------------------------------------------
# Compute output persistence
# ---------------------------------------------------------------------------

def save_compute_result(use_case_id: str, result: ComputeResult) -> None:
    path = _compute_output_path(use_case_id, result.module_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result.model_dump(), f, indent=2)


def load_compute_result(use_case_id: str, module_id: str) -> Optional[ComputeResult]:
    path = _compute_output_path(use_case_id, module_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return ComputeResult(**data)
    except Exception:
        logger.exception("Failed to load compute result: %s / %s", use_case_id, module_id)
        return None
