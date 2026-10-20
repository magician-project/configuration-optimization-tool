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


def test_top_level_dimensions_question_does_not_crash_on_input(qapp):
    """Regression test: a top-level (non-follow-up) "dimensions" question, like
    q2_camera_resolution, used to crash with "takes 3 positional arguments but 4
    were given" because _on_dimension_changed was hardcoded for the q6_dimensions
    follow-up's 2-arg signature while this widget called it with 3 args."""
    questions = [{
        "id": "q_test_resolution",
        "title": "test",
        "type": "dimensions",
        "fields": [
            {"id": "width", "label": "Width (px)"},
            {"id": "height", "label": "Height (px)"},
        ],
        "units": ["px"],
        "default_unit": "px",
    }]
    form = QuestionnaireForm(questions=questions)

    form._widgets["q_test_resolution_width"].setValue(2464)
    form._widgets["q_test_resolution_height"].setValue(2056)

    assert form.get_answers()["q_test_resolution"] == {"width": 2464, "height": 2056}


def test_dimensions_answers_round_trip_through_load_answers(qapp):
    """Saved dict-valued dimensions answers must repopulate their sub-widgets."""
    questions = [{
        "id": "q_test_resolution",
        "title": "test",
        "type": "dimensions",
        "fields": [
            {"id": "width", "label": "Width (px)"},
            {"id": "height", "label": "Height (px)"},
        ],
        "units": ["px"],
        "default_unit": "px",
    }]
    form = QuestionnaireForm(questions=questions)

    form.load_answers({"q_test_resolution": {"width": 2464, "height": 2056}})

    assert form._widgets["q_test_resolution_width"].value() == pytest.approx(2464)
    assert form._widgets["q_test_resolution_height"].value() == pytest.approx(2056)


def test_select_follow_up_is_visible_after_reload(qapp):
    """Regression test: reopening a use case restores combo-box values with
    blocked signals (to avoid feedback loops), so _on_select_changed never
    runs and a follow-up like q2_camera_spec stayed hidden even though its
    value was loaded. load_answers must re-show it via _update_conditional_visibility."""
    questions = [{
        "id": "q_test_camera_type",
        "title": "test",
        "type": "select",
        "options": [
            {"value": "standard", "label": "Standard"},
            {"value": "gige", "label": "GiGE"},
        ],
        "follow_up": {
            "condition": {"field": "q_test_camera_type", "operator": "in", "values": ["gige"]},
            "question": {"id": "q_test_camera_spec", "type": "text", "label": "Model:"},
        },
    }]
    form = QuestionnaireForm(questions=questions)
    follow_up_widget = form._widgets["q_test_camera_spec"].parent()

    form.load_answers({"q_test_camera_type": "gige", "q_test_camera_spec": "Sony XCG-CP510"})

    assert form._widgets["q_test_camera_spec"].text() == "Sony XCG-CP510"
    assert not follow_up_widget.isHidden()


def _sensor_section(form):
    [card] = [w for w in form._conditional_widgets if w.property("question_condition")["field"] == "q_pipeline"]
    return card


def test_sensor_section_hidden_for_grinding_only(qapp):
    form = QuestionnaireForm()

    form.load_answers({"q_pipeline": "grinding"})
    assert _sensor_section(form).isHidden()

    form.load_answers({"q_pipeline": "both"})
    assert not _sensor_section(form).isHidden()


def test_sensor_section_visible_when_pipeline_unanswered(qapp):
    form = QuestionnaireForm()

    form.load_answers({})

    assert not _sensor_section(form).isHidden()
