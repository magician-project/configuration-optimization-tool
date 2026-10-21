"""
Guards UseCasePage._finish_compute(): a compute that completes after its module has
left scope (pipeline changed while it was running) must not bring the module back.
"""

import json

import pytest
from PySide6.QtWidgets import QApplication

from datetime import datetime, timezone

from app.engine.questionnaire_engine import apply_impacts_to_modules, compute_impacts
from app.models.questionnaire import QuestionnaireAnswers
from app.models.use_case import UseCase
from app.storage import json_store


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.mark.parametrize("pipeline, module_id, expected_status", [
    ("inspection", "orienteering_solver", "out_of_scope"),
    (None, "grabber", "not_assessed"),
])
def test_late_compute_result_is_discarded_for_module_without_scope(
    qapp, tmp_path, monkeypatch, pipeline, module_id, expected_status
):
    monkeypatch.setattr(json_store, "_DATA_DIR", str(tmp_path))
    now = datetime.now(timezone.utc).isoformat()
    uc = UseCase(id="late", name="Late", created_at=now, updated_at=now,
                 answers=QuestionnaireAnswers(q_pipeline=pipeline))
    apply_impacts_to_modules(uc, compute_impacts(uc.answers, module_answers={}))
    json_store.save(uc)
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps({"module_id": module_id, "success": True}))

    from gui.pages.use_case_page import UseCasePage
    page = UseCasePage("late")

    page._finish_compute(module_id, True, str(result_path))

    module = page._use_case.modules[module_id]
    assert module.status == expected_status
    assert module.compute_result is None
