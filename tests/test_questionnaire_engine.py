"""
Tests for the Motion Planner's multiple-robot-arms handling in
compute_impacts(): a flag alone does not make a module actionable in the
GUI (apply_impacts_to_modules derives status purely from impacts), so the
multi-arm warning must come with an impact too.
"""

from app.engine.questionnaire_engine import compute_impacts
from app.models.questionnaire import QuestionnaireAnswers


def test_multiple_arms_alone_produces_an_actionable_motion_planner_impact():
    answers = QuestionnaireAnswers(q1_robot_arms="multiple")

    result = compute_impacts(answers, module_answers={})

    mp = result["module_impacts"]["motion_planning"]
    assert mp["impacts"], "multi-arm selection must add an impact, not just a flag"
    assert any(f["id"] == "flag_mp_multi_arm" for f in mp["flags"])


def test_single_arm_adds_no_motion_planner_impact_or_flag():
    answers = QuestionnaireAnswers(q1_robot_arms="single")

    result = compute_impacts(answers, module_answers={})

    mp = result["module_impacts"]["motion_planning"]
    assert mp["impacts"] == []
    assert mp["flags"] == []
