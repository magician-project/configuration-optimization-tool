"""
result_freshness.py

Detects whether a module's compute result is out of date: whether the answers the
module's compute.py reads have changed since the result was computed.

compute.py merges the general answers with ``module_answers[<module>]``
(``{**answers, **module_answers[<module>]}``). The fingerprint hashes exactly
that merge, so answers of other modules never make a result out of date, and
reverting a change makes the result current again.
"""

from __future__ import annotations

import hashlib
import json

from app.models.use_case import UseCase


def answers_fingerprint(use_case: UseCase, module_id: str) -> str:
    """Fingerprint of the answers ``module_id``'s compute.py would read right now."""
    merged = {
        **use_case.answers.model_dump(mode="json"),
        **use_case.module_answers.get(module_id, {}),
    }
    canonical = json.dumps(merged, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def is_out_of_date(use_case: UseCase, module_id: str) -> bool:
    """True if the module has a compute result whose answers have changed since.

    A result without a fingerprint (computed before fingerprints existed) counts as
    out of date. A module without a compute result has nothing to be out of date.
    """
    ms = use_case.modules.get(module_id)
    if ms is None or ms.compute_result is None:
        return False
    return ms.computed_answers_fingerprint != answers_fingerprint(use_case, module_id)


def out_of_date_modules(use_case: UseCase) -> set[str]:
    """Ids of all modules whose compute result is out of date."""
    return {mid for mid in use_case.modules if is_out_of_date(use_case, mid)}
