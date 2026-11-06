"""
Impedance Controller — compute tests

Covers the ticket's acceptance criteria: the spec defaults, explicit answers (including zero),
force sync off until answered, the shared control rate read from the Cartesian Controller,
and the flat result.json contract.
"""

import json
import os

import pytest

from modules.impedance_controller.compute import deploy_blockers, main, notes, run
from modules.impedance_controller.ros_interface import get_commands

_SPEC_DEFAULTS = {
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


def test_unanswered_parameters_get_the_spec_defaults():
    outputs = run({})

    for key, default in _SPEC_DEFAULTS.items():
        assert outputs[key] == pytest.approx(default), key


def test_answers_override_the_defaults():
    outputs = run({"max_contact_force_n": 100.0, "admittance_gain": 0.002})

    assert outputs["max_contact_force_n"] == 100.0
    assert outputs["admittance_gain"] == 0.002
    assert outputs["touch_force_n"] == 10.0


def test_zero_is_an_answer_not_a_missing_value():
    assert run({"force_deadband_n": 0})["force_deadband_n"] == 0.0


def test_force_sync_is_off_until_answered():
    assert run({})["force_sync_enabled"] is False
    assert run({"force_sync_enabled": "no"})["force_sync_enabled"] is False
    assert run({"force_sync_enabled": "yes"})["force_sync_enabled"] is True


def test_the_wrench_topic_is_not_configured_here():
    assert "measured_wrench_topic" not in run({})


def test_nothing_blocks_deployment():
    assert deploy_blockers({}) == []


def test_notes_say_changes_need_a_restart_and_the_recipe_is_not_verified():
    joined = " ".join(notes({}))

    assert "restart" in joined
    assert "material-tool recipe" in joined


def test_ros_interface_only_returns_notes():
    commands = get_commands(run({}))

    assert commands and all(c.type == "note" for c in commands)


def _run_main(tmp_path, monkeypatch, module_answers):
    use_case = {"name": "Grinding cell", "answers": {}, "module_answers": module_answers}
    use_case_path = tmp_path / "use_case.json"
    use_case_path.write_text(json.dumps(use_case), encoding="utf-8")
    out_dir = tmp_path / "out"
    monkeypatch.setattr("sys.argv", ["compute", str(use_case_path), str(out_dir)])

    main()

    with open(os.path.join(out_dir, "result.json"), encoding="utf-8") as f:
        return json.load(f)


def test_main_writes_the_result_contract(tmp_path, monkeypatch):
    result = _run_main(tmp_path, monkeypatch, {"impedance_controller": {"touch_force_n": 12.0}})

    assert result["module_id"] == "impedance_controller"
    assert result["success"] is True
    assert result["outputs"]["touch_force_n"] == 12.0
    assert result["outputs"]["unload_threshold_n"] == 8.0
    assert result["deploy_blockers"] == []
    assert result["notes"]


def test_main_takes_the_control_rate_from_the_cartesian_controller(tmp_path, monkeypatch):
    result = _run_main(tmp_path, monkeypatch, {
        "cartesian_controller": {"control_rate_hz": 500.0},
        "impedance_controller": {"control_rate_hz": 250.0},
    })

    assert result["outputs"]["control_rate_hz"] == 500.0


def test_main_uses_the_default_control_rate_while_the_owner_has_not_set_one(tmp_path, monkeypatch):
    result = _run_main(tmp_path, monkeypatch, {"impedance_controller": {"control_rate_hz": 250.0}})

    assert result["outputs"]["control_rate_hz"] == 1000.0
