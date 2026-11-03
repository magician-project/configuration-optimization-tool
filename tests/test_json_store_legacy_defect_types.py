"""
A stored use case whose Q8 still holds the old defect types (dents, dirt,
surface_damage) loads with Q8 unanswered. Its stored derived state (confidence,
impacts, flags) must follow, in both loading paths, instead of keeping credit
and impacts for an answer that no longer exists.
"""

import json
from datetime import datetime, timezone

import pytest

from app.engine.questionnaire_engine import apply_impacts_to_modules, compute_impacts
from app.models.questionnaire import QuestionnaireAnswers
from app.models.use_case import Flag, UseCase
from app.storage import json_store

_ANSWERS = {"q_pipeline": "both", "q3_additional_sensors": ["tactile"]}


def _write_stored_use_case(data_dir, q8_defects: list) -> None:
    """Persist a use case as it was saved with a now-valid Q8, then put `q8_defects` in its file."""
    now = datetime.now(timezone.utc).isoformat()
    uc = UseCase(id="stored", name="Stored", created_at=now, updated_at=now,
                 answers=QuestionnaireAnswers(**_ANSWERS, q8_defects=["positive_dent"]))
    apply_impacts_to_modules(uc, compute_impacts(uc.answers, module_answers={}))
    uc.modules["tactile_sensor"].flags.append(Flag(
        id="flag_geometric_defects", type="warning", message="old flag", module_id="tactile_sensor",
    ))
    uc.modules["localiser"].status = "computed"
    data = uc.model_dump()
    data["answers"]["q8_defects"] = q8_defects
    folder = data_dir / "stored"
    folder.mkdir()
    (folder / "use_case.json").write_text(json.dumps(data), encoding="utf-8")


def _load(path: str) -> UseCase:
    return json_store.load("stored") if path == "load" else json_store.list_all()[0]


@pytest.mark.parametrize("path", ["load", "list_all"])
def test_old_q8_values_refresh_the_stored_derived_state(tmp_path, monkeypatch, path):
    monkeypatch.setattr(json_store, "_DATA_DIR", str(tmp_path))
    _write_stored_use_case(tmp_path, q8_defects=["dents", "surface_damage"])

    uc = _load(path)

    expected = compute_impacts(QuestionnaireAnswers(**_ANSWERS), module_answers={})
    assert uc.answers.q8_defects == []
    assert uc.confidence.score == expected["confidence"]["score"]
    for module_id in ("orienteering_solver", "tactile_sensor"):
        assert not [i for i in uc.modules[module_id].impacts if i.reason.startswith("Q8")]
    assert "flag_geometric_defects" not in [f.id for f in uc.modules["tactile_sensor"].flags]


@pytest.mark.parametrize("path", ["load", "list_all"])
def test_current_q8_values_keep_the_stored_lifecycle(tmp_path, monkeypatch, path):
    monkeypatch.setattr(json_store, "_DATA_DIR", str(tmp_path))
    _write_stored_use_case(tmp_path, q8_defects=["positive_dent"])

    uc = _load(path)

    assert uc.modules["localiser"].status == "computed"
