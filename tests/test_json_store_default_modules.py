"""
Guards against legacy use_case.json files (saved before default_modules existed)
getting stuck with the Pydantic field default [] forever instead of the
task-type fallback — see json_store._ensure_all_modules().
"""

from datetime import datetime, timezone

from app.models.questionnaire import QuestionnaireAnswers
from app.models.use_case import UseCase
from app.storage.json_store import _ensure_all_modules


def _legacy_use_case() -> UseCase:
    now = datetime.now(timezone.utc).isoformat()
    # Simulates data loaded from a pre-existing use_case.json: default_modules
    # was never written, so Pydantic parses it as the field default, [].
    return UseCase(id="legacy", name="Legacy", created_at=now, updated_at=now)


def test_ensure_all_modules_recomputes_default_modules_for_legacy_use_cases():
    uc = _legacy_use_case()
    uc.answers = QuestionnaireAnswers(q_pipeline="both")
    assert uc.default_modules == []

    _ensure_all_modules(uc)

    assert "orienteering_solver" in uc.default_modules
    assert "motion_planning" in uc.default_modules


def test_legacy_use_case_without_pipeline_loads_as_not_assessed():
    uc = _legacy_use_case()
    _ensure_all_modules(uc)
    uc.modules["grabber"].status = "needs_action"
    uc.modules["localiser"].status = "out_of_scope"

    _ensure_all_modules(uc)

    assert uc.default_modules == []
    assert {m.status for m in uc.modules.values()} == {"not_assessed"}


def test_not_assessed_load_keeps_advanced_lifecycle_status():
    uc = _legacy_use_case()
    _ensure_all_modules(uc)
    uc.modules["ergodic_control"].status = "computed"
    uc.modules["grabber"].status = "validated"

    _ensure_all_modules(uc)

    assert uc.modules["ergodic_control"].status == "computed"
    assert uc.modules["grabber"].status == "validated"
    assert uc.modules["localiser"].status == "not_assessed"


def test_not_assessed_modules_enter_scope_once_the_pipeline_is_answered():
    uc = _legacy_use_case()
    _ensure_all_modules(uc)
    uc.answers = QuestionnaireAnswers(q_pipeline="inspection")

    _ensure_all_modules(uc)

    assert uc.modules["grabber"].status == "ok"
    assert uc.modules["orienteering_solver"].status == "out_of_scope"


def test_ensure_all_modules_respects_an_existing_pipeline_answer():
    uc = _legacy_use_case()
    uc.answers = QuestionnaireAnswers(q_pipeline="inspection")

    _ensure_all_modules(uc)

    assert "orienteering_solver" not in uc.default_modules
    assert uc.modules["orienteering_solver"].status == "out_of_scope"


def test_legacy_task_type_answers_are_migrated_to_pipeline():
    assert QuestionnaireAnswers(q_task_type="grinding").q_pipeline == "both"
    assert QuestionnaireAnswers(q_task_type="inspection").q_pipeline == "inspection"
    assert QuestionnaireAnswers().q_pipeline is None


def test_legacy_disabled_status_is_reconciled_with_scope():
    uc = _legacy_use_case()
    uc.answers = QuestionnaireAnswers(q_pipeline="both")
    _ensure_all_modules(uc)
    uc.modules["grabber"].status = "disabled"  # left behind by the removed manual override

    _ensure_all_modules(uc)

    assert uc.modules["grabber"].status in ("ok", "needs_action")


def test_legacy_always_required_module_without_open_item_is_demoted_to_ready_to_validate():
    uc = _legacy_use_case()
    uc.answers = QuestionnaireAnswers(q_pipeline="both")
    _ensure_all_modules(uc)
    uc.modules["orienteering_solver"].status = "needs_action"  # saved while the solver was always-required
    uc.modules["ergodic_control"].status = "validated"

    _ensure_all_modules(uc)

    assert uc.modules["orienteering_solver"].status == "ok"
    assert uc.modules["ergodic_control"].status == "validated"

