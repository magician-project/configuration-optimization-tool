"""
Tests for validate_configuration(): which inputs an in-scope module needs from outside
the pipeline selection, and the resulting configuration validation status.
"""

from app.engine.module_dependencies import validate_configuration
from app.models.use_case import ExternalSource


_CONTROLLER_DEPENDENCIES = [
    "dmp_to_cartesian_controller", "dmp_to_impedance_controller", "impedance_controller_to_cartesian_controller",
]

_SOLVER_SOURCE = ExternalSource(source_name="Partner AOI", contract_agreed=True)
_WRENCH_SOURCE = ExternalSource(source_name="Partner F/T", contract_agreed=True)
_GRABBER_WRENCH = {"impedance_controller": {"measured_wrench_source": "grabber"}}
_EXTERNAL_WRENCH = {
    "impedance_controller": {"measured_wrench_source": "external", "measured_wrench_topic": "/partner/wrench"},
}


def _wrench(validation):
    [capability] = [c for c in validation.capabilities if c.capability == "measured_wrench"]
    return capability


def _requirement(validation, dependency_id):
    [req] = [r for r in validation.external_inputs if r.dependency_id == dependency_id]
    return req


def test_both_pipelines_need_no_external_input():
    result = validate_configuration("both", ["tactile"], module_answers=_GRABBER_WRENCH)

    assert result.status == "valid"
    assert result.external_inputs == []
    assert "estimation_to_orienteering_solver" in result.satisfied


def test_inspection_only_is_valid():
    assert validate_configuration("inspection").status == "valid"


def test_grinding_only_requires_external_defect_input():
    result = validate_configuration("grinding")

    req = _requirement(result, "estimation_to_orienteering_solver")
    assert req.consumer == "orienteering_solver"
    assert req.input_name == "defects"
    assert req.provider_name == "Estimation Algorithm"
    assert "defect.severity" in req.minimum_fields
    assert result.status == "invalid"


def test_grinding_only_with_named_source_but_no_agreed_contract_is_incomplete():
    sources = {
        "estimation_to_orienteering_solver": ExternalSource(source_name="Partner AOI"),
        "measured_wrench": _WRENCH_SOURCE,
    }

    result = validate_configuration("grinding", external_sources=sources, module_answers=_EXTERNAL_WRENCH)

    assert result.status == "incomplete"


def test_grinding_only_with_agreed_source_is_valid_with_external_inputs():
    sources = {"estimation_to_orienteering_solver": _SOLVER_SOURCE, "measured_wrench": _WRENCH_SOURCE}

    result = validate_configuration("grinding", external_sources=sources, module_answers=_EXTERNAL_WRENCH)

    assert result.status == "valid_with_external_inputs"
    assert all(r.complete for r in result.external_inputs)


def test_external_source_kept_for_out_of_scope_dependency_is_not_counted():
    sources = {"estimation_to_orienteering_solver": _SOLVER_SOURCE}

    result = validate_configuration("both", ["tactile"], sources, _GRABBER_WRENCH)

    assert result.status == "valid"


def test_dmp_is_a_cot_module_consuming_the_ordered_grinding_targets():
    from app.engine.module_dependencies import DEPENDENCIES, NON_COT_NODES, scope_for

    [dep] = [d for d in DEPENDENCIES if d.id == "orienteering_solver_to_dmp"]

    assert dep.consumer == "dmp"
    assert dep.consumer_input == "ordered grinding targets (defect class, pose, frame_id)"
    assert "dmp_motion_planner" not in NON_COT_NODES
    assert "dmp_motion_planner" not in scope_for("both")


def test_dmp_is_in_scope_for_grinding_and_both_but_not_inspection():
    from app.engine.module_dependencies import scope_for

    assert "dmp" in scope_for("grinding")
    assert "dmp" in scope_for("both")
    assert "dmp" not in scope_for("inspection")


def test_dmp_needs_the_orienteering_solver_and_is_satisfied_when_it_is_in_scope():
    result = validate_configuration("both", ["tactile"], module_answers=_GRABBER_WRENCH)

    assert "orienteering_solver_to_dmp" in result.satisfied
    assert result.status == "valid"


def test_dmp_to_the_controllers_is_verified_and_required_but_impedance_to_cartesian_is_not_confirmed():
    from app.engine.module_dependencies import DEPENDENCIES

    by_id = {d.id: d for d in DEPENDENCIES}

    assert [(by_id[i].provider, by_id[i].consumer) for i in _CONTROLLER_DEPENDENCIES] == [
        ("dmp", "cartesian_controller"),
        ("dmp", "impedance_controller"),
        ("impedance_controller", "cartesian_controller"),
    ]
    for dep_id in _CONTROLLER_DEPENDENCIES[:2]:
        dep = by_id[dep_id]
        assert not dep.display_only and not dep.external_input_allowed and dep.verified
    assert by_id[_CONTROLLER_DEPENDENCIES[2]].display_only


def test_grinding_use_case_satisfies_the_dmp_to_controller_dependencies():
    for pipeline in ("grinding", "both"):
        result = validate_configuration(pipeline)

        assert result.owner_confirmation_needed == []
        assert set(_CONTROLLER_DEPENDENCIES[:2]) <= set(result.satisfied)
        assert _CONTROLLER_DEPENDENCIES[2] not in result.satisfied


def test_controllers_are_in_scope_for_grinding_and_both_but_not_inspection():
    from app.engine.module_dependencies import scope_for

    for module_id in ("cartesian_controller", "impedance_controller"):
        assert module_id in scope_for("grinding")
        assert module_id in scope_for("both")
        assert module_id not in scope_for("inspection")


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


# --- Required capabilities ------------------------------------------------------------------------


def test_grinding_only_without_an_external_wrench_source_needs_external_input_and_blocks_deploy():
    from app.engine.module_dependencies import capability_deploy_blockers

    result = validate_configuration("grinding")

    req = _requirement(result, "measured_wrench")
    assert req.consumer == "impedance_controller" and req.kind == "capability" and not req.complete
    assert result.status == "invalid"
    assert capability_deploy_blockers(result, "impedance_controller")


def test_grinding_only_with_a_grabber_source_is_a_blocker_because_the_grabber_is_out_of_scope():
    result = validate_configuration("grinding", ["tactile"], module_answers=_GRABBER_WRENCH)

    assert result.status == "invalid"
    assert not _wrench(result).satisfied
    assert "not in scope" in _wrench(result).blockers[0]
    assert [r for r in result.external_inputs if r.kind == "capability"] == []


def test_both_with_the_grabber_as_source_and_tactile_sensing_satisfies_the_capability():
    result = validate_configuration("both", ["tactile"], module_answers=_GRABBER_WRENCH)

    assert _wrench(result).satisfied and _wrench(result).provider == "grabber"
    assert "/magician_grabber/wrench_sensed" in _wrench(result).summary
    assert result.external_inputs == []


def test_both_with_the_grabber_as_source_but_without_tactile_sensing_is_a_blocker():
    result = validate_configuration("both", [], module_answers=_GRABBER_WRENCH)

    assert result.status == "invalid"
    assert "tactile" in _wrench(result).blockers[0]


def test_the_grabber_source_can_use_a_custom_topic():
    answers = {"impedance_controller": {"measured_wrench_source": "grabber", "measured_wrench_topic": "/ft/custom"}}

    assert "/ft/custom" in _wrench(validate_configuration("both", ["tactile"], module_answers=answers)).summary


def test_both_without_a_chosen_source_is_a_blocker_even_with_tactile_sensing():
    result = validate_configuration("both", ["tactile"])

    assert result.status == "invalid"
    assert "choose a source" in _wrench(result).blockers[0]


def test_an_external_source_needs_a_topic():
    answers = {"impedance_controller": {"measured_wrench_source": "external"}}

    result = validate_configuration("both", ["tactile"], {"measured_wrench": _WRENCH_SOURCE}, answers)

    assert result.status == "invalid"
    assert "measured_wrench_topic" in _wrench(result).blockers[0]


def test_an_unsupported_wrench_source_is_a_blocker_and_raises_no_external_input():
    answers = {"impedance_controller": {"measured_wrench_source": "foo", "measured_wrench_topic": "/ft"}}

    for pipeline in ("grinding", "both"):
        result = validate_configuration(pipeline, ["tactile"], module_answers=answers)

        assert result.status == "invalid"
        assert "unsupported source 'foo'" in _wrench(result).blockers[0]
        assert [r for r in result.external_inputs if r.kind == "capability"] == []


def test_an_external_wrench_source_with_topic_and_agreed_contract_is_satisfied():
    result = validate_configuration(
        "both", ["tactile"], {"measured_wrench": _WRENCH_SOURCE}, _EXTERNAL_WRENCH,
    )

    assert result.status == "valid_with_external_inputs"
    assert _wrench(result).satisfied and _wrench(result).provider == "external"
    assert "Partner F/T" in _wrench(result).summary


def test_an_external_wrench_source_without_a_name_blocks_deploy_but_only_makes_the_status_incomplete():
    from app.engine.module_dependencies import capability_deploy_blockers

    result = validate_configuration("both", ["tactile"], module_answers=_EXTERNAL_WRENCH)

    assert result.status == "incomplete"
    assert capability_deploy_blockers(result, "impedance_controller") == [
        "measured wrench: name the external source"
    ]


def test_the_capability_source_is_kept_per_capability_id_not_per_dependency():
    result = validate_configuration("both", ["tactile"], module_answers=_EXTERNAL_WRENCH)

    assert _requirement(result, "measured_wrench").minimum_fields == ["measured_wrench_topic"]


def test_the_dmp_target_frame_comes_from_the_localiser_with_its_default_frame():
    for pipeline in ("grinding", "both"):
        [frame] = [c for c in validate_configuration(pipeline).capabilities if c.capability == "target_frame"]

        assert frame.consumer == "dmp" and frame.provider == "localiser" and frame.satisfied
        assert frame.summary == "Target frame: fender (Localiser)"


def test_the_dmp_target_frame_follows_the_localiser_mesh_frame():
    answers = {"localiser": {"q_local_mesh_link": "car_body_frame"}}

    [frame] = [
        c for c in validate_configuration("grinding", module_answers=answers).capabilities
        if c.capability == "target_frame"
    ]

    assert frame.summary == "Target frame: car_body_frame (Localiser)"


def test_capabilities_are_only_evaluated_for_consumers_in_scope():
    assert validate_configuration("inspection").capabilities == []
    assert validate_configuration(None).capabilities == []


def test_capabilities_never_become_dependencies_or_arrows():
    from app.engine.module_dependencies import REQUIRED_CAPABILITIES, DEPENDENCIES, visible_dependency_edges, scope_for

    capability_ids = {c.id for c in REQUIRED_CAPABILITIES}

    assert not capability_ids & {d.id for d in DEPENDENCIES}
    assert not {c.consumer for c in REQUIRED_CAPABILITIES} - set(scope_for("both"))
    assert all(e.provider not in capability_ids for e in visible_dependency_edges(scope_for("both", ["tactile"])))


def test_a_capability_never_pulls_a_module_into_scope():
    from app.engine.module_dependencies import scope_for

    assert "grabber" not in scope_for("grinding", ["tactile"])


def test_the_defect_type_and_frame_are_minimum_fields_of_the_external_handover():
    [req] = [
        r for r in validate_configuration("grinding").external_inputs
        if r.dependency_id == "estimation_to_orienteering_solver"
    ]

    assert {"defect.type", "coordinate_frame.frame_id"} <= set(req.minimum_fields)
    assert not {"defect.type", "coordinate_frame.frame_id"} & set(req.conditional_fields)
    assert any("defect class" in note for note in req.field_notes)
    assert any("Localiser" in note for note in req.field_notes)


def test_a_missing_wrench_source_makes_the_impedance_controller_need_action_until_agreed():
    from app.engine.questionnaire_engine import sync_external_input_status

    uc = _grinding_use_case()
    assert uc.modules["impedance_controller"].status == "needs_action"

    uc.module_answers["impedance_controller"] = _EXTERNAL_WRENCH["impedance_controller"]
    uc.external_sources["measured_wrench"] = _WRENCH_SOURCE
    sync_external_input_status(uc)

    assert uc.modules["impedance_controller"].status == "ok"


def _both_use_case_with_tactile():
    uc = _grinding_use_case()
    uc.answers.q_pipeline = "both"
    uc.answers.q3_additional_sensors = ["tactile"]
    return uc


def test_an_unanswered_wrench_source_needs_action_even_though_no_external_input_is_raised():
    from app.engine.questionnaire_engine import apply_impacts_to_modules, compute_impacts

    uc = _both_use_case_with_tactile()

    apply_impacts_to_modules(uc, compute_impacts(uc.answers, module_answers=uc.module_answers))

    assert validate_configuration("both", ["tactile"]).external_inputs == []
    assert uc.modules["impedance_controller"].status == "needs_action"


def test_choosing_a_valid_wrench_source_makes_the_impedance_controller_ready_again():
    from app.engine.questionnaire_engine import apply_impacts_to_modules, compute_impacts

    uc = _both_use_case_with_tactile()
    apply_impacts_to_modules(uc, compute_impacts(uc.answers, module_answers=uc.module_answers))

    uc.module_answers.update(_GRABBER_WRENCH)
    apply_impacts_to_modules(uc, compute_impacts(uc.answers, module_answers=uc.module_answers))

    assert uc.modules["impedance_controller"].status == "ok"


def test_an_agreed_external_wrench_source_without_a_topic_still_needs_action():
    from app.engine.questionnaire_engine import apply_impacts_to_modules, compute_impacts

    uc = _both_use_case_with_tactile()
    uc.module_answers["impedance_controller"] = {"measured_wrench_source": "external"}
    uc.external_sources["measured_wrench"] = _WRENCH_SOURCE

    apply_impacts_to_modules(uc, compute_impacts(uc.answers, module_answers=uc.module_answers))

    assert uc.modules["impedance_controller"].status == "needs_action"


def test_an_open_capability_does_not_reset_advanced_lifecycle_status():
    from app.engine.questionnaire_engine import sync_external_input_status

    uc = _both_use_case_with_tactile()
    uc.modules["impedance_controller"].status = "computed"

    sync_external_input_status(uc)

    assert uc.modules["impedance_controller"].status == "computed"


