"""
Cartesian Controller — compute tests

Covers the ticket's acceptance criteria: the spec defaults, explicit answers (including zero),
the fixed unload mode, the flat result.json contract, and that nothing can block deployment.
"""

import json
import os

import pytest

from modules.cartesian_controller.compute import deploy_blockers, main, notes, run
from modules.cartesian_controller.ros_interface import get_commands

_SPEC_DEFAULTS = {
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


def test_unanswered_parameters_get_the_spec_defaults():
    outputs = run({})

    for key, default in _SPEC_DEFAULTS.items():
        assert outputs[key] == pytest.approx(default), key


def test_answers_override_the_defaults():
    outputs = run({"reach_duration_s": 12.5, "control_rate_hz": 500.0})

    assert outputs["reach_duration_s"] == 12.5
    assert outputs["control_rate_hz"] == 500.0
    assert outputs["touch_dwell_s"] == 3.0


def test_zero_is_an_answer_not_a_missing_value():
    assert run({"touch_dwell_s": 0})["touch_dwell_s"] == 0.0


def test_unload_mode_is_always_smooth_retract():
    assert run({})["unload_mode"] == "smooth retract"


def test_outputs_are_flat_str_or_float():
    assert all(isinstance(v, (str, int, float)) for v in run({}).values())


def test_nothing_blocks_deployment():
    assert deploy_blockers({}) == []


def test_notes_say_changes_need_a_restart_and_time_feasibility_is_not_checked():
    joined = " ".join(notes({}))

    assert "restart" in joined
    assert "time constraint" in joined


def test_ros_interface_only_returns_notes():
    commands = get_commands(run({}))

    assert commands and all(c.type == "note" for c in commands)


def test_main_writes_the_result_contract(tmp_path, monkeypatch):
    use_case = {
        "name": "Grinding cell",
        "answers": {},
        "module_answers": {"cartesian_controller": {"go_away_distance_m": 0.2}},
    }
    use_case_path = tmp_path / "use_case.json"
    use_case_path.write_text(json.dumps(use_case), encoding="utf-8")
    out_dir = tmp_path / "out"
    monkeypatch.setattr("sys.argv", ["compute", str(use_case_path), str(out_dir)])

    main()

    with open(os.path.join(out_dir, "result.json"), encoding="utf-8") as f:
        result = json.load(f)
    assert result["module_id"] == "cartesian_controller"
    assert result["success"] is True
    assert result["outputs"]["go_away_distance_m"] == 0.2
    assert result["outputs"]["reach_duration_s"] == 10.0
    assert result["deploy_blockers"] == []
    assert result["notes"]
