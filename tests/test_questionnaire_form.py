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


_PRIMITIVES = {
    "id": "primitives",
    "type": "collection",
    "title": "Grinding primitives",
    "tooltip": "Paths per defect class.",
    "driver": {"field": "q8_defects", "options": ["positive_dent", "negative_dent"]},
    "item_fields": [
        {"id": "pose_path", "label": "Pose path", "type": "text"},
        {"id": "wrench_path", "label": "Wrench path", "type": "text"},
    ],
}


def _shown_rows(form):
    """(option, field) pairs whose input the user would see once the form is shown."""
    return {
        tuple(key.split(".")[1:]) for key, w in form._widgets.items()
        if key.startswith("primitives.") and w.isVisibleTo(form)
    }


def test_collection_shows_one_row_per_selected_allowed_driver_option(qapp):
    form = QuestionnaireForm(
        questions=[_PRIMITIVES], general_answers={"q8_defects": ["negative_dent", "other"]},
    )

    assert _shown_rows(form) == {("negative_dent", "pose_path"), ("negative_dent", "wrench_path")}


def test_collection_rows_follow_a_changed_driver(qapp):
    form = QuestionnaireForm(questions=[_PRIMITIVES], general_answers={"q8_defects": ["negative_dent"]})

    form.set_general_answers({"q8_defects": ["positive_dent"]})

    assert _shown_rows(form) == {("positive_dent", "pose_path"), ("positive_dent", "wrench_path")}


def test_collection_shows_no_rows_while_the_driver_is_unanswered(qapp):
    form = QuestionnaireForm(questions=[_PRIMITIVES])

    assert _shown_rows(form) == set()


def test_collection_answers_are_stored_per_option_and_item_field(qapp):
    form = QuestionnaireForm(questions=[_PRIMITIVES], general_answers={"q8_defects": ["positive_dent"]})

    form._widgets["primitives.positive_dent.pose_path"].setText("/prim/pos_pose.csv")
    form._widgets["primitives.positive_dent.wrench_path"].setText("/prim/pos_wrench.csv")

    assert form.get_answers() == {
        "primitives": {"positive_dent": {"pose_path": "/prim/pos_pose.csv", "wrench_path": "/prim/pos_wrench.csv"}},
    }


def test_clearing_every_collection_field_leaves_no_answer(qapp):
    form = QuestionnaireForm(questions=[_PRIMITIVES], general_answers={"q8_defects": ["positive_dent"]})
    pose = form._widgets["primitives.positive_dent.pose_path"]

    pose.setText("/prim/pos_pose.csv")
    pose.setText("")

    assert form.get_answers() == {}


def test_collection_answers_reload_into_their_rows(qapp):
    form = QuestionnaireForm(questions=[_PRIMITIVES], general_answers={"q8_defects": ["negative_dent"]})

    form.load_answers({"primitives": {"negative_dent": {"pose_path": "/prim/neg_pose.csv"}}})

    assert form._widgets["primitives.negative_dent.pose_path"].text() == "/prim/neg_pose.csv"
    assert form._widgets["primitives.negative_dent.wrench_path"].text() == ""


def test_values_of_a_deselected_option_return_when_it_is_reselected(qapp):
    saved = {"primitives": {"positive_dent": {"pose_path": "/prim/pos_pose.csv"}}}
    form = QuestionnaireForm(questions=[_PRIMITIVES], general_answers={"q8_defects": ["negative_dent"]})
    form.load_answers(saved)

    form.set_general_answers({"q8_defects": ["positive_dent"]})

    assert ("positive_dent", "pose_path") in _shown_rows(form)
    assert form._widgets["primitives.positive_dent.pose_path"].text() == "/prim/pos_pose.csv"
    assert form.get_answers() == saved


def test_editing_a_reloaded_collection_leaves_the_saved_answers_untouched(qapp):
    saved = {"primitives": {"positive_dent": {"pose_path": "/prim/pos_pose.csv"}}}
    form = QuestionnaireForm(questions=[_PRIMITIVES], general_answers={"q8_defects": ["positive_dent"]})
    form.load_answers(saved)

    form._widgets["primitives.positive_dent.pose_path"].setText("/prim/other.csv")

    assert saved == {"primitives": {"positive_dent": {"pose_path": "/prim/pos_pose.csv"}}}
