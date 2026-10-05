"""
Tests for QuestionnaireForm's number_float widget construction.

QDoubleSpinBox rounds setMinimum()/setMaximum()/setValue() to whatever
decimals precision is currently set on the widget, so decimals/step must
be applied before min/max/value or a small min (e.g. 0.0001) silently
becomes 0.00.
"""

import pytest

from PySide6.QtWidgets import QApplication

from gui.components.questionnaire_form import QuestionnaireForm


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_small_min_is_not_rounded_away_by_default_precision(qapp):
    questions = [{
        "id": "q_test_dt",
        "title": "test",
        "type": "number_float",
        "min": 0.0001,
        "max": 1.0,
        "decimals": 6,
        "step": 0.0001,
        "default": 0.001,
    }]
    form = QuestionnaireForm(questions=questions)
    widget = form._widgets["q_test_dt"]

    assert widget.decimals() == 6
    assert widget.minimum() == pytest.approx(0.0001)
    assert widget.value() == pytest.approx(0.001)


def test_default_precision_is_unchanged_for_fields_without_overrides(qapp):
    questions = [{
        "id": "q_test_offset",
        "title": "test",
        "type": "number_float",
        "min": 0.0,
        "max": 10.0,
        "default": 0.05,
    }]
    form = QuestionnaireForm(questions=questions)
    widget = form._widgets["q_test_offset"]

    assert widget.decimals() == 2
    assert widget.singleStep() == pytest.approx(0.01)
