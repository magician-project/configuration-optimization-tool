"""
Guards UseCasePage._finish_compute(): a compute that completes after its module has
left scope (pipeline changed while it was running) must not bring the module back.
Also guards UseCasePage._deploy_module(): result notes are shown, and stale results
of modules that evaluate deploy blockers must be recomputed.
"""

import json

import pytest
from PySide6.QtWidgets import QApplication

from datetime import datetime, timezone

from app.engine.questionnaire_engine import apply_impacts_to_modules, compute_impacts
from app.models.questionnaire import QuestionnaireAnswers
from app.models.use_case import ComputeResult, UseCase
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


def _page_with_computed_module(tmp_path, monkeypatch, module_id, **result_fields):
    monkeypatch.setattr(json_store, "_DATA_DIR", str(tmp_path))
    now = datetime.now(timezone.utc).isoformat()
    uc = UseCase(id="deploy", name="Deploy", created_at=now, updated_at=now,
                 answers=QuestionnaireAnswers(q_pipeline="both", q3_additional_sensors=["tactile"]))
    apply_impacts_to_modules(uc, compute_impacts(uc.answers, module_answers={}))
    module = uc.modules[module_id]
    module.compute_result = ComputeResult(module_id=module_id, success=True, outputs={}, **result_fields)
    module.status = "computed"
    json_store.save(uc)

    from gui.pages import use_case_page
    warnings, infos = [], []
    monkeypatch.setattr(use_case_page.QMessageBox, "warning", lambda *args: warnings.append(args[1:]))
    monkeypatch.setattr(use_case_page.QMessageBox, "information", lambda *args: infos.append(args[1:]))
    monkeypatch.setattr(use_case_page, "get_adapter", lambda: _SucceedingAdapter())
    return use_case_page.UseCasePage("deploy"), warnings, infos


class _SucceedingAdapter:
    def apply_commands(self, module_id, commands):
        return {"success": True}


def test_deploy_shows_the_module_notes(qapp, tmp_path, monkeypatch):
    note = "defect class mapping not verified with module owner"
    page, warnings, infos = _page_with_computed_module(
        tmp_path, monkeypatch, "orienteering_solver", deploy_blockers=[], notes=[note],
    )

    page._deploy_module("orienteering_solver")

    assert warnings == []
    assert page._use_case.modules["orienteering_solver"].status == "deployed"
    [(_title, message)] = infos
    assert note in message


def test_deploy_without_notes_shows_no_notes_dialog(qapp, tmp_path, monkeypatch):
    page, warnings, infos = _page_with_computed_module(tmp_path, monkeypatch, "localiser", deploy_blockers=[])

    page._deploy_module("localiser")

    assert page._use_case.modules["localiser"].status == "deployed"
    assert (warnings, infos) == ([], [])


@pytest.mark.parametrize("module_id", ["tactile_sensor", "orienteering_solver", "ergodic_control"])
def test_q8_consumer_result_without_evaluated_blockers_must_be_recomputed(qapp, tmp_path, monkeypatch, module_id):
    page, warnings, _infos = _page_with_computed_module(tmp_path, monkeypatch, module_id)

    page._deploy_module(module_id)

    [(title, message)] = warnings
    assert title == "Cannot deploy"
    assert "Run Compute again" in message
    assert page._use_case.modules[module_id].status == "computed"
