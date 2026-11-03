"""A compute result is out of date once the answers its module used have changed."""

from datetime import datetime, timezone

from app.engine.questionnaire_engine import apply_impacts_to_modules, compute_impacts
from app.engine.result_freshness import answers_fingerprint, is_out_of_date
from app.models.questionnaire import QuestionnaireAnswers
from app.models.use_case import ComputeResult, UseCase


def _computed_use_case(module_id: str = "grabber") -> UseCase:
    now = datetime.now(timezone.utc).isoformat()
    uc = UseCase(
        id="fresh", name="Fresh", created_at=now, updated_at=now,
        answers=QuestionnaireAnswers(q_pipeline="inspection"),
        module_answers={"grabber": {"q_grab_lighting_mode": "none"}, "localiser": {"q_local_setup": "cell_a"}},
    )
    apply_impacts_to_modules(uc, compute_impacts(uc.answers, uc.module_answers))
    ms = uc.modules[module_id]
    ms.compute_result = ComputeResult(module_id=module_id, success=True)
    ms.computed_answers_fingerprint = answers_fingerprint(uc, module_id)
    return uc


def test_a_fresh_result_is_not_out_of_date():
    assert not is_out_of_date(_computed_use_case(), "grabber")


def test_changing_a_general_answer_makes_the_result_out_of_date_and_reverting_makes_it_current():
    uc = _computed_use_case()

    uc.answers.q_pipeline = "both"
    assert is_out_of_date(uc, "grabber")

    uc.answers.q_pipeline = "inspection"
    assert not is_out_of_date(uc, "grabber")


def test_changing_the_module_answers_makes_the_result_out_of_date_and_reverting_makes_it_current():
    uc = _computed_use_case()

    uc.module_answers["grabber"]["q_grab_lighting_mode"] = "ring"
    assert is_out_of_date(uc, "grabber")

    uc.module_answers["grabber"]["q_grab_lighting_mode"] = "none"
    assert not is_out_of_date(uc, "grabber")


def test_changing_another_modules_answers_does_not_make_the_result_out_of_date():
    uc = _computed_use_case()

    uc.module_answers["localiser"]["q_local_setup"] = "cell_b"
    uc.module_answers["motion_planning"] = {"q_mp_planner": "rrt"}

    assert not is_out_of_date(uc, "grabber")


def test_a_result_without_fingerprint_is_out_of_date():
    uc = _computed_use_case()
    uc.modules["grabber"].computed_answers_fingerprint = None

    assert is_out_of_date(uc, "grabber")


def test_a_module_without_result_is_not_out_of_date():
    uc = _computed_use_case()
    uc.modules["grabber"].compute_result = None

    assert not is_out_of_date(uc, "grabber")


def test_re_evaluating_impacts_keeps_the_compute_result_so_it_can_be_judged():
    uc = _computed_use_case()
    computed = uc.modules["grabber"]
    computed.computed_at = "2026-11-03T12:00:00+00:00"
    computed.status = "computed"

    uc.module_answers["localiser"]["q_local_setup"] = "cell_b"
    apply_impacts_to_modules(uc, compute_impacts(uc.answers, uc.module_answers))

    kept = uc.modules["grabber"]
    assert kept.compute_result is not None
    assert kept.computed_at == "2026-11-03T12:00:00+00:00"
    assert not is_out_of_date(uc, "grabber")
    assert kept.status in ("ok", "needs_action")

    uc.answers.q_pipeline = "both"
    apply_impacts_to_modules(uc, compute_impacts(uc.answers, uc.module_answers))

    assert is_out_of_date(uc, "grabber")
