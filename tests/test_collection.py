"""
Tests for the collection question type's engine helpers: which driver options
are active, and which part of the general questionnaire a module form may read.
"""

import pytest

from app.engine.collection import active_items, collection_options, driver_answers, selected_options

PRIMITIVES = {
    "id": "primitives",
    "type": "collection",
    "title": "Grinding primitives",
    "driver": {"field": "q8_defects", "options": ["positive_dent", "negative_dent"]},
    "item_fields": [
        {"id": "pose_path", "label": "Pose path", "type": "text"},
        {"id": "wrench_path", "label": "Wrench path", "type": "text"},
    ],
}


def test_only_selected_options_that_the_driver_filter_allows_are_active():
    driver = {"q8_defects": ["other", "negative_dent", "positive_dent"]}

    assert selected_options(PRIMITIVES, driver) == ["positive_dent", "negative_dent"]


def test_without_a_filter_every_driver_option_can_be_active():
    unfiltered = {**PRIMITIVES, "driver": {"field": "q8_defects"}}

    assert selected_options(unfiltered, {"q8_defects": ["other"]}) == ["other"]


def test_nothing_is_active_while_the_driver_is_unanswered():
    assert selected_options(PRIMITIVES, {}) == []


def test_a_filter_naming_an_option_the_driver_lacks_is_rejected():
    typo = {**PRIMITIVES, "driver": {"field": "q8_defects", "options": ["positive_dents"]}}

    with pytest.raises(ValueError, match="positive_dents"):
        collection_options(typo)


def test_a_driver_outside_the_general_questionnaire_is_rejected():
    module_driver = {**PRIMITIVES, "driver": {"field": "q_mp_base_link"}}

    with pytest.raises(ValueError, match="q_mp_base_link"):
        collection_options(module_driver)


def test_a_single_choice_driver_is_rejected():
    # Only a multi-select (checkbox) answer is a list of selected options.
    select_driver = {**PRIMITIVES, "driver": {"field": "q_pipeline"}}

    with pytest.raises(ValueError, match="checkbox"):
        collection_options(select_driver)


def test_values_of_a_deselected_option_are_kept_but_ignored():
    stored = {
        "positive_dent": {"pose_path": "/p/pose.csv", "wrench_path": "/p/wrench.csv"},
        "negative_dent": {"pose_path": "/n/pose.csv"},
    }

    active = active_items(PRIMITIVES, stored, {"q8_defects": ["negative_dent"]})

    assert active == {"negative_dent": {"pose_path": "/n/pose.csv"}}
    assert "positive_dent" in stored


def test_a_selected_option_without_answers_is_active_with_empty_fields():
    active = active_items(PRIMITIVES, None, {"q8_defects": ["positive_dent"]})

    assert active == {"positive_dent": {}}


def test_a_module_form_can_read_only_the_drivers_its_questions_declare():
    general = {"q8_defects": ["positive_dent"], "q_pipeline": "grinding", "q8_other_defect": "scratch"}
    questions = [{"id": "q_plain", "type": "text"}, PRIMITIVES]

    assert driver_answers(questions, general) == {"q8_defects": ["positive_dent"]}


def test_a_module_without_collections_reads_nothing_from_the_general_questionnaire():
    assert driver_answers([{"id": "q_plain", "type": "text"}], {"q8_defects": ["positive_dent"]}) == {}
