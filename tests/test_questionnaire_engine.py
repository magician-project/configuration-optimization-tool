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


def test_unanswered_pipeline_leaves_every_module_not_assessed():
    uc = _new_use_case()
    uc.answers = QuestionnaireAnswers(q1_robot_arms="multiple")  # would give impacts if scope were known

    apply_impacts_to_modules(uc, compute_impacts(uc.answers, module_answers={}))

    assert uc.default_modules == []
    assert {m.status for m in uc.modules.values()} == {"not_assessed"}
    assert all(m.impacts == [] and m.flags == [] for m in uc.modules.values())


def test_answering_the_pipeline_brings_not_assessed_modules_into_scope():
    uc = _new_use_case()
    apply_impacts_to_modules(uc, compute_impacts(uc.answers, module_answers={}))
    uc.answers = QuestionnaireAnswers(q_pipeline="both", q1_robot_arms="multiple")

    apply_impacts_to_modules(uc, compute_impacts(uc.answers, module_answers={}))

    assert uc.modules["grabber"].status == "needs_action"
    assert uc.modules["orienteering_solver"].status == "needs_action"
    assert "not_assessed" not in {m.status for m in uc.modules.values()}


def test_grinding_only_confidence_ignores_inspection_categories():
    answers = QuestionnaireAnswers(q_pipeline="grinding", q1_robot_arms="single")

    confidence = compute_impacts(answers, module_answers={})["confidence"]

    assert confidence["max"] == 5
    assert confidence["score"] == 1


def test_grinding_only_ignores_retained_inspection_answers_for_cross_cutting_flag():
    answers = QuestionnaireAnswers(
        q_pipeline="grinding",
        q2_camera_type="gige",
        q2_camera_resolution={"width": 1920, "height": 1080},
        q2_camera_framerate=30,
        q2_stream_shm="yes",
        q4_lighting="additional",
        q9_time="tight",
        q9_time_value=10,
    )

    solver = compute_impacts(answers, module_answers={})["module_impacts"]["orienteering_solver"]

    assert solver["impacts"], "time constraint should still affect the solver"
    assert all(f["id"] != "flag_cross_cutting" for f in solver["flags"])



def test_retained_tactile_answer_does_not_affect_motion_planner_for_grinding_only():
    grinding = QuestionnaireAnswers(q_pipeline="grinding", q3_additional_sensors=["tactile"])
    both = QuestionnaireAnswers(q_pipeline="both", q3_additional_sensors=["tactile"])

    grinding_mp = compute_impacts(grinding, module_answers={})["module_impacts"]["motion_planning"]
    both_mp = compute_impacts(both, module_answers={})["module_impacts"]["motion_planning"]

    assert grinding_mp["impacts"] == []
    assert both_mp["impacts"]

