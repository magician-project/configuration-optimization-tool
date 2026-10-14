"""
Guards the Ticket-2 acceptance criterion: a module override must survive a
real save/reload round trip through json_store, not just an in-memory
pydantic round trip.
"""

from datetime import datetime, timezone

import app.storage.json_store as json_store
from app.engine.questionnaire_engine import apply_impacts_to_modules, compute_impacts
from app.models.use_case import UseCase


def _new_use_case(use_case_id: str) -> UseCase:
    now = datetime.now(timezone.utc).isoformat()
    return UseCase(id=use_case_id, name="Test", created_at=now, updated_at=now)


def test_module_override_survives_save_and_reload(tmp_path, monkeypatch):
    monkeypatch.setattr(json_store, "_DATA_DIR", str(tmp_path))

    uc = _new_use_case("override-roundtrip")
    uc.module_overrides["tactile_sensor"] = False
    # Mirrors what the toggle handler in use_case_page does: recompute before saving.
    apply_impacts_to_modules(
        uc, compute_impacts(uc.answers, module_answers=uc.module_answers, module_overrides=uc.module_overrides)
    )
    json_store.save(uc)

    reloaded = json_store.load("override-roundtrip")

    assert reloaded is not None
    assert reloaded.module_overrides["tactile_sensor"] is False
    assert reloaded.modules["tactile_sensor"].status == "disabled"
