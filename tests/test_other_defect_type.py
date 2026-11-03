"""Q8 defect classes: Positive Dent, Negative Dent and a described Other, mapped per module."""

import json
import sys

import pytest

from app.engine.questionnaire_engine import compute_impacts
from app.engine.schema import SCHEMA
from app.models.questionnaire import QuestionnaireAnswers
from app.models.use_case import UseCase
from modules.ergodic_control import compute as ergodic
from modules.orienteering_solver import compute as orienteering
from modules.tactile_sensor import compute as tactile

_NOT_VERIFIED = "defect class mapping not verified with module owner"


def _defects_question() -> dict:
    return next(q for q in SCHEMA["questions"] if q["id"] == "q8_defects")


def _confidence_score(answers: QuestionnaireAnswers) -> int:
    return compute_impacts(answers, module_answers={})["confidence"]["score"]


def _impact_texts(answers: QuestionnaireAnswers, module_id: str) -> list:
    module = compute_impacts(answers, module_answers={})["module_impacts"][module_id]
    return [i["what_changes"] for i in module["impacts"] if i["reason"].startswith("Q8")]


# ---------------------------------------------------------------------------
# Questionnaire
# ---------------------------------------------------------------------------

def test_q8_offers_only_the_canonical_defect_classes():
    question = _defects_question()

    assert question["title"] == "Defect classes"
    assert [(o["value"], o["label"]) for o in question["options"]] == [
        ("positive_dent", "Positive Dent"),
        ("negative_dent", "Negative Dent"),
        ("other", "Other"),
    ]


def test_other_defect_class_asks_for_a_required_description():
    follow_up = _defects_question()["follow_up"]

    assert follow_up["condition"] == {"field": "q8_defects", "operator": "contains", "value": "other"}
    assert follow_up["question"]["id"] == "q8_other_defect"
    assert follow_up["question"]["type"] == "text"
    assert "required" in follow_up["question"]["label"]


# ---------------------------------------------------------------------------
# Loading: no migration of the old values
# ---------------------------------------------------------------------------

def test_use_case_with_only_old_q8_values_loads_with_q8_unanswered():
    stored = {
        "id": "old", "name": "Old", "created_at": "", "updated_at": "",
        "answers": {"q_pipeline": "both", "q8_defects": ["dents", "dirt", "surface_damage"]},
    }

    answers = UseCase(**json.loads(json.dumps(stored))).answers

    assert answers.q8_defects == []
    assert _impact_texts(answers, "orienteering_solver") == []
    assert _confidence_score(answers) == _confidence_score(QuestionnaireAnswers(q_pipeline="both"))


def test_old_q8_values_are_dropped_and_defect_classes_kept():
    answers = QuestionnaireAnswers(q8_defects=["dents", "positive_dent", "other"], q8_other_defect="scratch")

    assert answers.q8_defects == ["positive_dent", "other"]


# ---------------------------------------------------------------------------
# Impacts
# ---------------------------------------------------------------------------

def test_impacts_name_the_defect_classes_and_the_other_description():
    answers = QuestionnaireAnswers(
        q_pipeline="both", q3_additional_sensors=["tactile"],
        q8_defects=["positive_dent", "negative_dent", "other"], q8_other_defect="scratch",
    )

    for module_id in ("orienteering_solver", "tactile_sensor"):
        [text] = _impact_texts(answers, module_id)
        assert "Positive Dent, Negative Dent, scratch" in text


def test_other_defect_class_without_description_is_shown_as_unspecified():
    answers = QuestionnaireAnswers(q8_defects=["other"])

    [text] = _impact_texts(answers, "orienteering_solver")

    assert "(other \u2014 unspecified)" in text


@pytest.mark.parametrize("defects", [["positive_dent"], ["negative_dent"], ["other"]])
def test_geometric_defects_flag_no_longer_exists(defects):
    answers = QuestionnaireAnswers(
        q_pipeline="both", q3_additional_sensors=["tactile"], q8_defects=defects, q8_other_defect="scratch",
    )

    impacts = compute_impacts(answers, module_answers={})["module_impacts"]

    flag_ids = [f["id"] for module in impacts.values() for f in module["flags"]]
    assert "flag_geometric_defects" not in flag_ids


# ---------------------------------------------------------------------------
# Tactile Classifier: confirmed mapping to POSITIVE / NEGATIVE
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("defects, expected", [
    (["positive_dent"], "POSITIVE"),
    (["negative_dent"], "NEGATIVE"),
    (["positive_dent", "negative_dent"], "POSITIVE,NEGATIVE"),
    (["positive_dent", "other"], "POSITIVE"),
    (["dents", "negative_dent"], "NEGATIVE"),
    ([], "unspecified"),
])
def test_tactile_maps_defect_classes_to_its_interface_labels(tmp_path, defects, expected):
    answers = {"q8_defects": defects, "q8_other_defect": "scratch"}

    assert tactile.run(answers, str(tmp_path))["defect_types"] == expected


def test_tactile_dents_are_deployable():
    assert tactile.deploy_blockers({"q8_defects": ["positive_dent", "negative_dent"]}) == []


def test_tactile_other_defect_class_blocks_deploy_and_names_the_description():
    blockers = tactile.deploy_blockers({"q8_defects": ["positive_dent", "other"], "q8_other_defect": "scratch"})

    assert len(blockers) == 1
    assert "'scratch'" in blockers[0]


# ---------------------------------------------------------------------------
# Orienteering Solver and Ergodic Control: canonical values, mapping not verified
# ---------------------------------------------------------------------------

def _run_unverified(module, answers: dict, tmp_path) -> dict:
    return module.run(answers) if module is orienteering else module.run(answers, str(tmp_path))


_UNVERIFIED_MODULES = pytest.mark.parametrize("module", [orienteering, ergodic], ids=["orienteering", "ergodic"])


@_UNVERIFIED_MODULES
@pytest.mark.parametrize("answers, expected", [
    ({"q8_defects": ["positive_dent", "negative_dent", "other"], "q8_other_defect": "scratch"},
     "positive_dent,negative_dent,scratch"),
    ({"q8_defects": ["other"]}, "other"),
    ({"q8_defects": ["dents", "positive_dent"]}, "positive_dent"),
    ({"q8_defects": ["dirt"]}, "unspecified"),
])
def test_unverified_modules_pass_the_canonical_defect_classes(tmp_path, module, answers, expected):
    assert _run_unverified(module, answers, tmp_path)["defect_types"] == expected


@_UNVERIFIED_MODULES
def test_unverified_modules_note_the_mapping_without_blocking_other(module):
    answers = {"q8_defects": ["positive_dent", "other"], "q8_other_defect": "scratch"}

    assert module.notes(answers) == [_NOT_VERIFIED]
    assert module.deploy_blockers(answers) == []


@_UNVERIFIED_MODULES
def test_unverified_modules_have_no_mapping_note_without_defect_classes(module):
    assert module.notes({"q8_defects": []}) == []


# ---------------------------------------------------------------------------
# Description is required for Other, in every module that consumes Q8
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("module", [tactile, orienteering, ergodic], ids=["tactile", "orienteering", "ergodic"])
def test_other_defect_class_without_description_blocks_deploy(module):
    blockers = module.deploy_blockers({"q8_defects": ["other"], "q8_other_defect": "  "})

    assert "describe the other defect class (Q8)" in blockers


@pytest.mark.parametrize("module", [tactile, orienteering, ergodic], ids=["tactile", "orienteering", "ergodic"])
def test_other_description_with_a_comma_blocks_deploy(module):
    # defect_types is comma-separated, so a comma would split one class into several.
    blockers = module.deploy_blockers({"q8_defects": ["other"], "q8_other_defect": "scratch, corrosion"})

    assert "describe one other defect class, without commas (Q8)" in blockers


def test_other_description_placeholder_names_a_single_class():
    assert "," not in _defects_question()["follow_up"]["question"]["placeholder"]


# ---------------------------------------------------------------------------
# result.json: blockers and notes are top-level, next to outputs
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("module, module_id, expected_notes, expected_blockers", [
    (tactile, "tactile_sensor", [], 1),
    (orienteering, "orienteering_solver", [_NOT_VERIFIED], 0),
    (ergodic, "ergodic_control", [_NOT_VERIFIED], 0),
])
def test_main_writes_blockers_and_notes_next_to_outputs(
    tmp_path, monkeypatch, module, module_id, expected_notes, expected_blockers
):
    use_case = {"name": "q8", "answers": {"q8_defects": ["positive_dent", "other"], "q8_other_defect": "scratch"}}
    uc_path = tmp_path / "use_case.json"
    uc_path.write_text(json.dumps(use_case), encoding="utf-8")
    out_dir = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["compute.py", str(uc_path), str(out_dir)])

    module.main()

    result = json.loads((out_dir / "result.json").read_text(encoding="utf-8"))
    assert result["module_id"] == module_id
    assert result["notes"] == expected_notes
    assert len(result["deploy_blockers"]) == expected_blockers
    assert "notes" not in result["outputs"]
    assert "deploy_blockers" not in result["outputs"]
