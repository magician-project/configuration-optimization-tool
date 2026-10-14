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


def test_apply_impacts_recomputes_default_modules_from_task_type():
    uc = _new_use_case()
    uc.answers = QuestionnaireAnswers(q_task_type="inspection")

    apply_impacts_to_modules(uc, compute_impacts(uc.answers, module_answers={}))

    assert set(uc.default_modules) == {"grabber", "localiser", "vision_classifier", "ergodic_control"}


def test_apply_impacts_falls_back_to_grinding_when_task_type_unanswered():
    uc = _new_use_case()  # q_task_type left at its default (None) — backward compatibility

    apply_impacts_to_modules(uc, compute_impacts(uc.answers, module_answers={}))

    assert "orienteering_solver" in uc.default_modules
    assert "motion_planning" in uc.default_modules


def test_overridden_off_module_gets_no_impacts_or_flags():
    answers = QuestionnaireAnswers(q1_robot_arms="multiple")

    result = compute_impacts(answers, module_answers={}, module_overrides={"orienteering_solver": False})

    op = result["module_impacts"]["orienteering_solver"]
    assert op["impacts"] == []
    assert op["flags"] == []
    # Other modules triggered by the same answer are unaffected
    assert result["module_impacts"]["grabber"]["impacts"]


def test_overridden_off_module_is_excluded_from_cross_cutting_flag_count():
    # 5+ characteristics triggers a cross-cutting flag naming every affected module
    answers = QuestionnaireAnswers(
        q1_robot_arms="multiple", q2_camera_type="gige", q4_lighting="additional",
        q5_materials=["metal"], q8_defects=["dents"],
    )

    result = compute_impacts(answers, module_answers={}, module_overrides={"orienteering_solver": False})

    assert result["module_impacts"]["orienteering_solver"]["flags"] == []
    assert any(f["id"] == "flag_cross_cutting" for f in result["module_impacts"]["grabber"]["flags"])


def test_apply_impacts_sets_disabled_status_for_overridden_off_module():
    uc = _new_use_case()
    uc.answers = QuestionnaireAnswers(q1_robot_arms="multiple")
    uc.module_overrides["orienteering_solver"] = False

    result = compute_impacts(uc.answers, module_answers={}, module_overrides=uc.module_overrides)
    apply_impacts_to_modules(uc, result)

    assert uc.modules["orienteering_solver"].status == "disabled"
    assert uc.modules["orienteering_solver"].impacts == []
    # Unrelated module keeps its normal, impact-driven status
    assert uc.modules["grabber"].status == "needs_action"


def test_re_enabling_a_module_recomputes_its_status_from_current_answers():
    uc = _new_use_case()
    uc.answers = QuestionnaireAnswers(q1_robot_arms="multiple")
    uc.module_overrides["orienteering_solver"] = False
    apply_impacts_to_modules(
        uc, compute_impacts(uc.answers, module_answers={}, module_overrides=uc.module_overrides)
    )
    assert uc.modules["orienteering_solver"].status == "disabled"

    uc.module_overrides["orienteering_solver"] = True
    apply_impacts_to_modules(
        uc, compute_impacts(uc.answers, module_answers={}, module_overrides=uc.module_overrides)
    )

    assert uc.modules["orienteering_solver"].status == "needs_action"
    assert uc.modules["orienteering_solver"].impacts
