"""
Tests for the Motion Planner's multiple-robot-arms handling in
compute_impacts(): a flag alone does not make a module actionable in the
GUI (apply_impacts_to_modules derives status purely from impacts), so the
multi-arm warning must come with an impact too.
"""

from datetime import datetime, timezone

from app.engine.questionnaire_engine import compute_impacts, apply_impacts_to_modules
from app.models.questionnaire import QuestionnaireAnswers
from app.models.use_case import UseCase


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


def _new_use_case() -> UseCase:
    now = datetime.now(timezone.utc).isoformat()
    return UseCase(id="test", name="Test", created_at=now, updated_at=now)


def test_apply_impacts_recomputes_default_modules_from_pipeline():
    uc = _new_use_case()
    uc.answers = QuestionnaireAnswers(q_pipeline="inspection")

    apply_impacts_to_modules(uc, compute_impacts(uc.answers, module_answers={}))

    assert set(uc.default_modules) == {
        "grabber", "vision_classifier", "ergodic_control", "localiser", "motion_planning",
    }
    assert uc.modules["orienteering_solver"].status == "out_of_scope"


def test_out_of_scope_module_gets_no_impacts_or_flags():
    answers = QuestionnaireAnswers(q_pipeline="inspection", q1_robot_arms="multiple")

    result = compute_impacts(answers, module_answers={})

    assert result["module_impacts"]["orienteering_solver"] == {"impacts": [], "flags": []}
    assert result["module_impacts"]["motion_planning"]["impacts"]


def test_apply_impacts_falls_back_to_both_when_pipeline_unanswered():
    uc = _new_use_case()  # q_pipeline left at its default (None) — backward compatibility

    apply_impacts_to_modules(uc, compute_impacts(uc.answers, module_answers={}))

    assert "orienteering_solver" in uc.default_modules
    assert "grabber" in uc.default_modules


def test_grinding_only_confidence_ignores_inspection_categories():
    answers = QuestionnaireAnswers(q_pipeline="grinding", q1_robot_arms="single")

    confidence = compute_impacts(answers, module_answers={})["confidence"]

    assert confidence["max"] == 5
    assert confidence["score"] == 1
