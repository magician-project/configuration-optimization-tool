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


def test_late_compute_result_is_discarded_for_out_of_scope_module(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(json_store, "_DATA_DIR", str(tmp_path))
    now = datetime.now(timezone.utc).isoformat()
    uc = UseCase(id="late", name="Late", created_at=now, updated_at=now,
                 answers=QuestionnaireAnswers(q_pipeline="inspection"))
    apply_impacts_to_modules(uc, compute_impacts(uc.answers, module_answers={}))
    json_store.save(uc)
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps({"module_id": "orienteering_solver", "success": True}))

    from gui.pages.use_case_page import UseCasePage
    page = UseCasePage("late")

    page._finish_compute("orienteering_solver", True, str(result_path))

    solver = page._use_case.modules["orienteering_solver"]
    assert solver.status == "out_of_scope"
    assert solver.compute_result is None
