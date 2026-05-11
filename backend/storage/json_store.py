import json
import os
import logging
from typing import Optional, List
from models.use_case import UseCase

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "use_cases")


def _ensure_dir() -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)


def _path(use_case_id: str) -> str:
    # Sanitize: only allow alphanumeric and hyphens to prevent path traversal
    safe_id = "".join(c for c in use_case_id if c.isalnum() or c == "-")
    return os.path.join(_DATA_DIR, f"{safe_id}.json")


def save(use_case: UseCase) -> None:
    _ensure_dir()
    with open(_path(use_case.id), "w", encoding="utf-8") as f:
        json.dump(use_case.model_dump(), f, indent=2)


def load(use_case_id: str) -> Optional[UseCase]:
    path = _path(use_case_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return UseCase(**data)
    except Exception:
        logger.exception("Failed to load use case: %s", use_case_id)
        return None


def list_all() -> List[UseCase]:
    _ensure_dir()
    use_cases: List[UseCase] = []
    for fname in os.listdir(_DATA_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(_DATA_DIR, fname), encoding="utf-8") as f:
                data = json.load(f)
            use_cases.append(UseCase(**data))
        except Exception:
            logger.exception("Failed to load file: %s", fname)
    return sorted(use_cases, key=lambda u: u.created_at, reverse=True)


def delete(use_case_id: str) -> bool:
    path = _path(use_case_id)
    if not os.path.exists(path):
        return False
    os.remove(path)
    return True
