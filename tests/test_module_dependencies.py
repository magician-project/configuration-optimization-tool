"""
Tests for validate_configuration(): which inputs an in-scope module needs from outside
the pipeline selection, and the resulting configuration validation status.
"""

from app.engine.module_dependencies import validate_configuration
from app.models.use_case import ExternalSource


def test_both_pipelines_need_no_external_input():
    result = validate_configuration("both")

    assert result.status == "valid"
    assert result.external_inputs == []
    assert "estimation_to_orienteering_solver" in result.satisfied


def test_inspection_only_is_valid():
    assert validate_configuration("inspection").status == "valid"


def test_grinding_only_requires_external_defect_input():
    result = validate_configuration("grinding")

    [req] = result.external_inputs
    assert req.consumer == "orienteering_solver"
    assert req.input_name == "defects"
    assert req.provider_name == "Estimation Algorithm"
    assert "defect.severity" in req.minimum_fields
    assert result.status == "incomplete"


def test_grinding_only_with_named_source_but_no_agreed_contract_is_incomplete():
    sources = {"estimation_to_orienteering_solver": ExternalSource(source_name="Partner AOI")}

    assert validate_configuration("grinding", external_sources=sources).status == "incomplete"


def test_grinding_only_with_agreed_source_is_valid_with_external_inputs():
    sources = {
        "estimation_to_orienteering_solver": ExternalSource(source_name="Partner AOI", contract_agreed=True)
    }

    result = validate_configuration("grinding", external_sources=sources)

    assert result.status == "valid_with_external_inputs"
    assert result.external_inputs[0].complete


def test_external_source_kept_for_out_of_scope_dependency_is_not_counted():
    sources = {
        "estimation_to_orienteering_solver": ExternalSource(source_name="Partner AOI", contract_agreed=True)
    }

    assert validate_configuration("both", external_sources=sources).status == "valid"


def test_unanswered_pipeline_is_not_assessed():
    result = validate_configuration(None)

    assert result.status == "not_assessed"
    assert result.external_inputs == []
    assert result.satisfied == []


def _grinding_use_case():
    from datetime import datetime, timezone

    from app.engine.questionnaire_engine import apply_impacts_to_modules, compute_impacts
    from app.models.questionnaire import QuestionnaireAnswers
    from app.models.use_case import UseCase

    now = datetime.now(timezone.utc).isoformat()
    uc = UseCase(id="g", name="G", created_at=now, updated_at=now,
                 answers=QuestionnaireAnswers(q_pipeline="grinding"))
    apply_impacts_to_modules(uc, compute_impacts(uc.answers, module_answers={}))
    return uc


def test_consumer_of_missing_external_input_needs_action():
    uc = _grinding_use_case()

    assert uc.modules["orienteering_solver"].status == "needs_action"
    assert uc.modules["localiser"].status == "ok"


def test_agreeing_the_external_source_makes_the_solver_ready_to_validate():
    from app.engine.questionnaire_engine import sync_external_input_status

    uc = _grinding_use_case()
    uc.external_sources["estimation_to_orienteering_solver"] = ExternalSource(
        source_name="Partner AOI", contract_agreed=True
    )

    sync_external_input_status(uc)

    assert uc.modules["orienteering_solver"].status == "ok"


def test_in_scope_module_without_open_item_is_ready_to_validate():
    from app.engine.questionnaire_engine import apply_impacts_to_modules, compute_impacts

    uc = _grinding_use_case()
    uc.answers.q_pipeline = "both"

    apply_impacts_to_modules(uc, compute_impacts(uc.answers, module_answers={}))

    assert uc.modules["orienteering_solver"].status == "ok"
    assert uc.modules["ergodic_control"].status == "ok"


def test_pending_external_input_does_not_reset_advanced_lifecycle_status():
    from app.engine.questionnaire_engine import sync_external_input_status

    uc = _grinding_use_case()
    for status in ("validated", "computed", "deployed"):
        uc.modules["orienteering_solver"].status = status

        sync_external_input_status(uc)

        assert uc.modules["orienteering_solver"].status == status

