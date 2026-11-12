"""UseCasePage: two steps, the modules step stays locked until a pipeline selection is saved."""

from datetime import datetime, timezone

import pytest
from PySide6.QtWidgets import QApplication

from app.engine.questionnaire_engine import apply_impacts_to_modules, compute_impacts
from app.models.questionnaire import QuestionnaireAnswers
from app.models.use_case import UseCase
from app.storage import json_store
from gui.pages.use_case_page import _STEP_MODULES, _STEP_SPECIFICATION, UseCasePage


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _page(tmp_path, monkeypatch, pipeline):
    monkeypatch.setattr(json_store, "_DATA_DIR", str(tmp_path))
    now = datetime.now(timezone.utc).isoformat()
    uc = UseCase(id="steps", name="Steps", created_at=now, updated_at=now,
                 answers=QuestionnaireAnswers(q_pipeline=pipeline))
    apply_impacts_to_modules(uc, compute_impacts(uc.answers, module_answers={}))
    json_store.save(uc)
    return UseCasePage("steps")


def test_a_new_use_case_opens_on_the_specification_with_the_modules_locked(qapp, tmp_path, monkeypatch):
    page = _page(tmp_path, monkeypatch, pipeline=None)

    assert page._steps.currentIndex() == _STEP_SPECIFICATION

    page._show_step(_STEP_MODULES)
    assert page._steps.currentIndex() == _STEP_SPECIFICATION


def test_a_specified_use_case_opens_on_its_modules(qapp, tmp_path, monkeypatch):
    page = _page(tmp_path, monkeypatch, pipeline="both")

    assert page._steps.currentIndex() == _STEP_MODULES


def test_next_saves_the_specification_and_continues_to_the_modules(qapp, tmp_path, monkeypatch):
    page = _page(tmp_path, monkeypatch, pipeline=None)
    page._on_answers_changed({**page._use_case.answers.model_dump(), "q_pipeline": "both"})

    page._on_next_step()

    assert json_store.load("steps").answers.q_pipeline == "both"
    assert page._steps.currentIndex() == _STEP_MODULES


def test_next_stays_on_the_specification_while_the_pipeline_is_unanswered(qapp, tmp_path, monkeypatch):
    page = _page(tmp_path, monkeypatch, pipeline=None)

    page._on_next_step()

    assert page._steps.currentIndex() == _STEP_SPECIFICATION


def test_the_specification_can_be_reopened_from_the_modules(qapp, tmp_path, monkeypatch):
    page = _page(tmp_path, monkeypatch, pipeline="both")

    page._show_step(_STEP_SPECIFICATION)

    assert page._steps.currentIndex() == _STEP_SPECIFICATION
