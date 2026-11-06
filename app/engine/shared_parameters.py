"""
Runtime parameters shared by several modules of the IIT grinding runtime (ADR-0005).

COT stores answers per module, so a shared parameter has one owner module whose answer is
the single source of truth. The other modules show it read-only and read the owner's value
in their compute, so their result also goes out of date when the owner changes it.
"""

from __future__ import annotations

from typing import Dict, Iterable, List

# parameter id -> (owner module, modules that only read it)
SHARED_PARAMETERS: Dict[str, tuple] = {
    "control_rate_hz": ("cartesian_controller", ("impedance_controller",)),
}


def shared_parameter_ids(module_id: str) -> List[str]:
    """Parameters ``module_id`` reads from another module's answers (read-only for it)."""
    return [pid for pid, (_, readers) in SHARED_PARAMETERS.items() if module_id in readers]


def shared_values(module_id: str, module_answers: Dict[str, dict]) -> dict:
    """The owner's current answers for the parameters ``module_id`` reads; unanswered ones are left out."""
    values = {}
    for pid in shared_parameter_ids(module_id):
        owner = SHARED_PARAMETERS[pid][0]
        value = (module_answers.get(owner) or {}).get(pid)
        if value is not None:
            values[pid] = value
    return values


def answers_with_shared(module_id: str, module_answers: Dict[str, dict]) -> dict:
    """``module_answers[module_id]`` with the shared parameters taken from their owners."""
    own = {
        k: v for k, v in (module_answers.get(module_id) or {}).items()
        if k not in shared_parameter_ids(module_id)
    }
    return {**own, **shared_values(module_id, module_answers)}


def without_shared(module_id: str, answers: dict) -> dict:
    """``answers`` minus the parameters ``module_id`` only reads (they must not be stored for it)."""
    read_only: Iterable[str] = shared_parameter_ids(module_id)
    return {k: v for k, v in answers.items() if k not in read_only}
