"""
Cartesian and Impedance Controller: spec parameters and defaults in the schemas, and the shared
`control_rate_hz` (owned by the Cartesian Controller, read-only for the Impedance Controller).
"""

from datetime import datetime, timezone

import pytest
from PySide6.QtWidgets import QApplication, QDoubleSpinBox

from app.engine.module_registry import MODULES, group_of
from app.engine.questionnaire_engine import apply_impacts_to_modules, compute_impacts
from app.engine.result_freshness import answers_fingerprint, is_out_of_date
from app.engine.schema import CARTESIAN_CONTROLLER_CONFIG, IMPEDANCE_CONTROLLER_CONFIG
from app.engine.shared_parameters import (
    SHARED_PARAMETERS, answers_with_shared, shared_parameter_ids, shared_values, without_shared,
)
from app.models.questionnaire import QuestionnaireAnswers
from app.models.use_case import ComputeResult, ModuleState, UseCase
from gui.components.module_detail import ModuleDetail

_CARTESIAN_PARAMETERS = {
    "reach_duration_s": 10.0,
    "touch_dwell_s": 3.0,
    "touch_approach_distance_m": 0.015,
    "unload_tail_window_s": 2.5,
    "unload_extra_duration_s": 2.0,
    "unload_retract_rate_m_s": 0.015,
    "go_away_distance_m": 0.10,
    "go_away_duration_s": 5.0,
    "control_rate_hz": 1000.0,
}

_IMPEDANCE_PARAMETERS = {
    "force_reference_scale": 1.0,
    "control_rate_hz": 1000.0,
    "admittance_gain": 0.0013,
    "force_rate_ff_scale": 0.6,
    "max_reference_force_rate": 220.0,
    "force_deadband_n": 2.0,
    "contact_threshold_n": 3.0,
    "max_normal_displacement_m": 0.12,
    "max_normal_velocity_m_s": 0.055,
    "contact_entry_velocity_m_s": 0.020,
    "max_contact_force_n": 150.0,
    "touch_force_n": 10.0,
    "force_sync_timeout_s": 4.0,
    "force_sync_tolerance_n": 2.0,
    "unload_threshold_n": 8.0,
}


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_both_controllers_form_the_controller_group():
    assert group_of("cartesian_controller") == "controller"
    assert group_of("impedance_controller") == "controller"
    assert MODULES["cartesian_controller"]["name"] == "Cartesian Controller"
    assert MODULES["impedance_controller"]["name"] == "Impedance Controller"


def test_cartesian_schema_asks_every_startup_parameter_with_its_spec_default():
    numbers = {q["id"]: q["default"] for q in CARTESIAN_CONTROLLER_CONFIG if q["type"] == "number_float"}

    assert numbers == pytest.approx(_CARTESIAN_PARAMETERS)
    assert "unload_mode" not in {q["id"] for q in CARTESIAN_CONTROLLER_CONFIG}


def test_impedance_schema_asks_every_startup_parameter_with_its_spec_default():
    by_id = {q["id"]: q for q in IMPEDANCE_CONTROLLER_CONFIG}

    assert {i: q["default"] for i, q in by_id.items() if q["type"] == "number_float"} == pytest.approx(
        _IMPEDANCE_PARAMETERS
    )
    assert by_id["force_sync_enabled"]["default"] == "no"
    assert not {"measured_wrench_topic", "unload_mode"} & set(by_id)


def test_the_shared_control_rate_is_read_only_only_for_the_reader():
    cartesian = {q["id"]: q for q in CARTESIAN_CONTROLLER_CONFIG}
    impedance = {q["id"]: q for q in IMPEDANCE_CONTROLLER_CONFIG}

    assert not cartesian["control_rate_hz"].get("read_only")
    assert impedance["control_rate_hz"]["read_only"] is True
    assert [q["id"] for q in IMPEDANCE_CONTROLLER_CONFIG if q.get("read_only")] == shared_parameter_ids(
        "impedance_controller"
    )


def test_the_control_rate_must_be_positive_in_both_controller_schemas():
    for config in (CARTESIAN_CONTROLLER_CONFIG, IMPEDANCE_CONTROLLER_CONFIG):
        [rate] = [q for q in config if q["id"] == "control_rate_hz"]

        assert rate["min"] > 0 and rate["default"] >= rate["min"]


def test_the_cartesian_controller_owns_the_control_rate():
    assert SHARED_PARAMETERS["control_rate_hz"][0] == "cartesian_controller"
    assert shared_parameter_ids("cartesian_controller") == []


def test_a_reader_gets_the_owners_value_and_its_own_stale_copy_is_ignored():
    module_answers = {
        "cartesian_controller": {"control_rate_hz": 500.0, "reach_duration_s": 12.0},
        "impedance_controller": {"control_rate_hz": 250.0, "touch_force_n": 12.0},
    }

    assert answers_with_shared("impedance_controller", module_answers) == {
        "touch_force_n": 12.0, "control_rate_hz": 500.0,
    }
    assert answers_with_shared("cartesian_controller", module_answers) == module_answers["cartesian_controller"]


def test_an_unset_owner_value_leaves_the_parameter_out():
    assert shared_values("impedance_controller", {}) == {}
    assert answers_with_shared("impedance_controller", {"impedance_controller": {"touch_force_n": 9.0}}) == {
        "touch_force_n": 9.0,
    }


def test_without_shared_drops_only_the_read_only_parameters():
    answers = {"control_rate_hz": 500.0, "touch_force_n": 9.0}

    assert without_shared("impedance_controller", answers) == {"touch_force_n": 9.0}
    assert without_shared("cartesian_controller", answers) == answers


def _dialog(module_id: str, module_config: dict, shared_answers: dict) -> ModuleDetail:
    info = MODULES[module_id]
    state = ModuleState(module_id=module_id, module_name=info["name"], description=info["description"], status="ok")
    return ModuleDetail(state, module_config=module_config, shared_answers=shared_answers)


def _spinbox(dlg: ModuleDetail, title: str) -> QDoubleSpinBox:
    form = dlg._config_form
    return form._widgets[title]


def test_impedance_tile_shows_the_cartesian_control_rate_read_only(qapp):
    dlg = _dialog("impedance_controller", {"touch_force_n": 12.0}, {"control_rate_hz": 500.0})

    box = _spinbox(dlg, "control_rate_hz")
    assert box.isReadOnly()
    assert box.value() == 500.0
    assert not _spinbox(dlg, "touch_force_n").isReadOnly()


def test_cartesian_tile_edits_the_control_rate(qapp):
    dlg = _dialog("cartesian_controller", {"control_rate_hz": 500.0}, {})

    box = _spinbox(dlg, "control_rate_hz")
    assert not box.isReadOnly()
    assert box.value() == 500.0


def test_saving_the_impedance_config_does_not_store_the_shared_control_rate(qapp):
    dlg = _dialog("impedance_controller", {}, {"control_rate_hz": 500.0})
    saved = []
    dlg.module_config_changed.connect(lambda module_id, config: saved.append((module_id, config)))

    _spinbox(dlg, "touch_force_n").setValue(12.0)
    dlg._save_config()

    assert saved == [("impedance_controller", {"touch_force_n": 12.0})]


def _use_case_with_results() -> UseCase:
    now = datetime.now(timezone.utc).isoformat()
    uc = UseCase(
        id="grind", name="Grind", created_at=now, updated_at=now,
        answers=QuestionnaireAnswers(q_pipeline="grinding"),
        module_answers={"cartesian_controller": {"control_rate_hz": 500.0}},
    )
    apply_impacts_to_modules(uc, compute_impacts(uc.answers, uc.module_answers))
    for module_id in ("cartesian_controller", "impedance_controller"):
        uc.modules[module_id].compute_result = ComputeResult(module_id=module_id, success=True)
        uc.modules[module_id].computed_answers_fingerprint = answers_fingerprint(uc, module_id)
    return uc


def test_changing_the_control_rate_makes_both_controller_results_out_of_date():
    uc = _use_case_with_results()
    assert not is_out_of_date(uc, "impedance_controller")

    uc.module_answers["cartesian_controller"]["control_rate_hz"] = 800.0

    assert is_out_of_date(uc, "cartesian_controller")
    assert is_out_of_date(uc, "impedance_controller")


def test_other_cartesian_answers_leave_the_impedance_result_current():
    uc = _use_case_with_results()

    uc.module_answers["cartesian_controller"]["reach_duration_s"] = 12.0

    assert not is_out_of_date(uc, "impedance_controller")


def test_a_grinding_use_case_has_both_controllers_in_scope_and_an_inspection_one_does_not():
    uc = _use_case_with_results()

    assert uc.modules["cartesian_controller"].status != "out_of_scope"
    assert uc.modules["impedance_controller"].status != "out_of_scope"

    uc.answers.q_pipeline = "inspection"
    apply_impacts_to_modules(uc, compute_impacts(uc.answers, uc.module_answers))

    assert uc.modules["cartesian_controller"].status == "out_of_scope"
    assert uc.modules["impedance_controller"].status == "out_of_scope"
