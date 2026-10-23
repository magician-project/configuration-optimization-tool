"""Q8 defect types: an "Other" option with a free-text follow-up, like Q5 materials."""

import pytest

from app.engine.questionnaire_engine import compute_impacts
from app.engine.schema import SCHEMA
from app.models.questionnaire import QuestionnaireAnswers
from modules.ergodic_control import compute as ergodic
from modules.orienteering_solver import compute as orienteering
from modules.tactile_sensor import compute as tactile


def _defects_question() -> dict:
    return next(q for q in SCHEMA["questions"] if q["id"] == "q8_defects")


def _impact_texts(answers: QuestionnaireAnswers, module_id: str) -> list:
    module = compute_impacts(answers, module_answers={})["module_impacts"][module_id]
    return [i["what_changes"] for i in module["impacts"] if i["reason"].startswith("Q8")]


def test_defects_question_offers_other_with_a_text_follow_up_shown_when_other_is_selected():
    question = _defects_question()

    assert "other" in [o["value"] for o in question["options"]]
    follow_up = question["follow_up"]
    assert follow_up["condition"] == {"field": "q8_defects", "operator": "contains", "value": "other"}
    assert follow_up["question"]["id"] == "q8_other_defect"
    assert follow_up["question"]["type"] == "text"


def test_other_defect_text_replaces_other_in_the_impacts():
    answers = QuestionnaireAnswers(
        q_pipeline="both", q3_additional_sensors=["tactile"],
        q8_defects=["dents", "other"], q8_other_defect="corrosion",
    )

    for module_id in ("orienteering_solver", "tactile_sensor"):
        [text] = _impact_texts(answers, module_id)
        assert "Dents/Deformations, corrosion" in text
        assert "other" not in text.lower().replace("another", "")


def test_other_defect_without_text_is_shown_as_unspecified():
    answers = QuestionnaireAnswers(q8_defects=["other"])

    [text] = _impact_texts(answers, "orienteering_solver")

    assert "(other \u2014 unspecified)" in text


def test_other_defect_is_not_treated_as_a_geometric_defect():
    answers = QuestionnaireAnswers(q8_defects=["other"], q8_other_defect="corrosion")

    flags = compute_impacts(answers, module_answers={})["module_impacts"]["tactile_sensor"]["flags"]

    assert "flag_geometric_defects" not in [f["id"] for f in flags]


@pytest.mark.parametrize("answers, expected", [
    ({"q8_defects": ["dents", "other"], "q8_other_defect": "corrosion"}, "dents,corrosion"),
    ({"q8_defects": ["other"]}, "other"),
    ({"q8_defects": ["dirt"]}, "dirt"),
])
def test_module_outputs_list_the_other_defect_by_name(tmp_path, answers, expected):
    assert orienteering.run(answers)["defect_types"] == expected
    assert tactile.run(answers, str(tmp_path))["defect_types"] == expected
    assert ergodic.run(answers, str(tmp_path))["defect_types"] == expected
