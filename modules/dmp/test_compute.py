"""
DMP — compute tests

Covers the ticket's acceptance criteria: the two paths per selected Positive/Negative Dent
(none for Other), every deploy blocker with its cause, and the flat result.json contract.
"""

import json
import os

import pytest

from modules.dmp.compute import deploy_blockers, main, notes, run
from modules.dmp.ros_interface import get_commands

_OFFSET = {"tool_defect_offset_x_m": "0.01", "tool_defect_offset_y_m": "-0.02", "tool_defect_offset_z_m": "0.15"}
_POSITIVE = {"pose_path": "/primitives/pos_pose.npy", "wrench_path": "/primitives/pos_wrench.npy"}
_NEGATIVE = {"pose_path": "/primitives/neg_pose.npy", "wrench_path": "/primitives/neg_wrench.npy"}


def _answers(defects=("positive_dent", "negative_dent"), primitives=None, **overrides):
    if primitives is None:
        primitives = {"positive_dent": _POSITIVE, "negative_dent": _NEGATIVE}
    return {"q8_defects": list(defects), "primitives": primitives, **_OFFSET, **overrides}


def test_complete_configuration_maps_the_classes_and_has_no_blockers():
    answers = _answers()

    outputs = run(answers)

    assert outputs["primitive_classes"] == "POSITIVE,NEGATIVE"
    assert outputs["primitive_positive_dent_pose_path"] == "/primitives/pos_pose.npy"
    assert outputs["primitive_positive_dent_wrench_path"] == "/primitives/pos_wrench.npy"
    assert outputs["primitive_negative_dent_pose_path"] == "/primitives/neg_pose.npy"
    assert outputs["primitive_negative_dent_wrench_path"] == "/primitives/neg_wrench.npy"
    assert deploy_blockers(answers) == []


def test_only_the_selected_classes_are_configured():
    answers = _answers(defects=["negative_dent"])

    outputs = run(answers)

    assert outputs["primitive_classes"] == "NEGATIVE"
    assert not any(key.startswith("primitive_positive_dent") for key in outputs)
    assert deploy_blockers(answers) == []


def test_paths_of_a_deselected_class_are_ignored():
    answers = _answers(defects=["negative_dent"], primitives={"positive_dent": _POSITIVE, "negative_dent": _NEGATIVE})

    assert "primitive_positive_dent_pose_path" not in run(answers)


def test_tool_offset_components_are_written_as_floats_in_metres():
    outputs = run(_answers())

    assert outputs["tool_defect_offset_x_m"] == pytest.approx(0.01)
    assert outputs["tool_defect_offset_y_m"] == pytest.approx(-0.02)
    assert outputs["tool_defect_offset_z_m"] == pytest.approx(0.15)


def test_orientation_mode_is_always_fixed():
    assert run(_answers())["orientation_mode"] == "fixed"
    assert run({})["orientation_mode"] == "fixed"


def test_offline_artifact_facts_are_read_only_information():
    outputs = run(_answers())

    assert outputs["rbf_basis_count"] == 24
    assert outputs["phase_samples"] == 256
    assert outputs["primitive_positive_dent_duration_s"] == pytest.approx(17.717)
    assert outputs["primitive_negative_dent_duration_s"] == pytest.approx(17.818)


def test_per_cycle_inputs_are_not_configured():
    outputs = run(_answers())

    assert not {"primitive_class", "defect_pose", "frame_id"} & set(outputs)


def test_outputs_are_flat():
    assert all(isinstance(v, (str, int, float)) for v in run(_answers()).values())


def test_no_defect_class_selected_blocks_deploy():
    blockers = deploy_blockers(_answers(defects=[], primitives={}))

    assert any("no defect class" in b for b in blockers)


def test_other_defect_class_blocks_deploy_and_names_the_description():
    answers = _answers(defects=["negative_dent", "other"], q8_other_defect="scratch")

    blockers = deploy_blockers(answers)

    assert "defect class 'scratch' has no learned grinding primitive" in blockers


def test_other_without_description_is_still_named_as_a_blocker():
    blockers = deploy_blockers(_answers(defects=["other"], primitives={}))

    assert "defect class 'other' has no learned grinding primitive" in blockers
    assert not any("no defect class" in b for b in blockers)


def test_other_is_never_asked_for_paths_nor_written_to_the_outputs():
    answers = _answers(defects=["negative_dent", "other"], q8_other_defect="scratch")

    outputs = run(answers)

    assert outputs["primitive_classes"] == "NEGATIVE"
    assert not any("other" in key or "scratch" in key for key in outputs)


@pytest.mark.parametrize("field", ["pose_path", "wrench_path"])
def test_a_missing_path_for_a_selected_class_blocks_deploy(field):
    positive = {k: v for k, v in _POSITIVE.items() if k != field}
    answers = _answers(primitives={"positive_dent": positive, "negative_dent": _NEGATIVE})

    blockers = deploy_blockers(answers)

    assert blockers == [f"Positive Dent: {field.replace('_', ' ')} is missing"]


def test_a_blank_path_counts_as_missing():
    positive = {**_POSITIVE, "pose_path": "   "}

    blockers = deploy_blockers(_answers(primitives={"positive_dent": positive, "negative_dent": _NEGATIVE}))

    assert blockers == ["Positive Dent: pose path is missing"]


def test_a_selected_class_without_any_answers_misses_both_paths():
    blockers = deploy_blockers(_answers(defects=["negative_dent"], primitives={}))

    assert blockers == ["Negative Dent: pose path is missing", "Negative Dent: wrench path is missing"]


@pytest.mark.parametrize("axis", ["x", "y", "z"])
def test_a_missing_offset_component_blocks_deploy(axis):
    answers = _answers()
    del answers[f"tool_defect_offset_{axis}_m"]

    assert deploy_blockers(answers) == [f"tool defect offset {axis} (m) is missing"]
    assert f"tool_defect_offset_{axis}_m" not in run(answers)


def test_a_blank_offset_component_counts_as_missing():
    assert deploy_blockers(_answers(tool_defect_offset_z_m="  ")) == ["tool defect offset z (m) is missing"]


@pytest.mark.parametrize("value", ["abc", "nan", "inf", "0,01"])
def test_an_offset_that_is_not_a_number_blocks_deploy_and_is_not_written(value):
    answers = _answers(tool_defect_offset_x_m=value)

    assert deploy_blockers(answers) == ["tool defect offset x (m) is not a number"]
    assert "tool_defect_offset_x_m" not in run(answers)


def test_zero_is_a_valid_offset():
    answers = _answers(tool_defect_offset_x_m="0")

    assert deploy_blockers(answers) == []
    assert run(answers)["tool_defect_offset_x_m"] == 0.0


@pytest.mark.parametrize("value", [0, 0.0])
def test_a_numeric_zero_offset_is_not_treated_as_missing(value):
    answers = _answers(tool_defect_offset_x_m=value)

    assert deploy_blockers(answers) == []
    assert run(answers)["tool_defect_offset_x_m"] == 0.0


def test_notes_say_what_cot_cannot_verify():
    joined = " ".join(notes(_answers()))

    assert "paths" in joined and "exist on the runtime" in joined
    assert "calibration" in joined


def test_ros_interface_only_returns_notes():
    commands = get_commands(run(_answers()))

    assert commands and all(c.type == "note" for c in commands)


def test_main_writes_the_result_contract(tmp_path, monkeypatch):
    use_case = {
        "name": "Grinding cell",
        "answers": {"q8_defects": ["positive_dent", "other"], "q8_other_defect": "scratch"},
        "module_answers": {"dmp": {"primitives": {"positive_dent": _POSITIVE}, **_OFFSET}},
    }
    use_case_path = tmp_path / "use_case.json"
    use_case_path.write_text(json.dumps(use_case), encoding="utf-8")
    out_dir = tmp_path / "out"
    monkeypatch.setattr("sys.argv", ["compute", str(use_case_path), str(out_dir)])

    main()

    with open(os.path.join(out_dir, "result.json"), encoding="utf-8") as f:
        result = json.load(f)
    assert result["module_id"] == "dmp"
    assert result["success"] is True
    assert result["outputs"]["primitive_classes"] == "POSITIVE"
    assert all(isinstance(v, (str, int, float)) for v in result["outputs"].values())
    assert result["deploy_blockers"] == ["defect class 'scratch' has no learned grinding primitive"]
    assert result["notes"]
