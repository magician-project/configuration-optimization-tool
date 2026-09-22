"""
Localiser — smoke tests

Covers the two paths the ticket's acceptance criteria care about:
registering a new Setup (mesh required) vs. reusing an already-registered
one (mesh irrelevant), plus static/dynamic output shape and result.json
round-tripping via main().
"""

import json
import os
import sys

from modules.localiser.compute import run, main
from modules.localiser.generate_config import write_config


def test_new_setup_without_mesh_is_blocked():
    outputs = run({"q_local_setup": "cell_a", "q_local_setup_registered": "no"})
    assert outputs["mesh_required"] == 1
    assert outputs["mesh_path"] == ""


def test_missing_setup_is_blocked():
    outputs = run({})
    assert outputs["setup_missing"] == 1

    outputs = run({"q_local_setup": "   "})
    assert outputs["setup_missing"] == 1

    outputs = run({"q_local_setup": "cell_a"})
    assert outputs["setup_missing"] == 0


def test_new_setup_with_mesh_is_not_blocked():
    outputs = run({
        "q_local_setup": "cell_a",
        "q_local_setup_registered": "no",
        "q_local_mesh_path": "/data/meshes/fender.stl",
    })
    assert outputs["mesh_required"] == 0
    assert outputs["mesh_path"] == "/data/meshes/fender.stl"


def test_existing_setup_without_mesh_is_not_blocked():
    outputs = run({"q_local_setup": "cell_a", "q_local_setup_registered": "yes"})
    assert outputs["mesh_required"] == 0
    assert outputs["setup_registered"] == 1


def test_static_mode_omits_slider_fields():
    outputs = run({"q_local_setup": "cell_a", "q_local_setup_registered": "yes"})
    assert outputs["motion_mode"] == "static"
    assert "slider_topic" not in outputs


def test_dynamic_mode_includes_slider_fields_with_defaults():
    outputs = run({
        "q_local_setup": "cell_a",
        "q_local_setup_registered": "yes",
        "q_local_motion_mode": "dynamic",
    })
    assert outputs["motion_mode"] == "dynamic"
    assert outputs["slider_topic"] == "/slider/position_y"
    assert outputs["slider_bias"] == 0.0
    assert outputs["publish_rate_hz"] == 30.0


def test_defaults_match_documented_frame_names():
    outputs = run({"q_local_setup": "cell_a", "q_local_setup_registered": "yes"})
    assert outputs["robot_base_link"] == "base_link"
    assert outputs["robot_ee_link"] == "tcp"
    assert outputs["mesh_link"] == "fender"
    assert outputs["database_file"] == "calibration_data.yaml"


def test_write_config_nests_params_under_ros_node_name(tmp_path):
    outputs = run({"q_local_setup": "cell_a", "q_local_setup_registered": "yes"})
    config_path = write_config(outputs, str(tmp_path))

    assert os.path.exists(config_path)
    import yaml
    with open(config_path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    assert doc["localisation"]["ros__parameters"]["setup"] == "cell_a"


def test_main_writes_result_json_for_both_paths(tmp_path, monkeypatch):
    use_case = {
        "name": "smoke",
        "answers": {"q7_mesh": "not_available"},
        "module_answers": {"localiser": {"q_local_setup": "cell_a", "q_local_setup_registered": "no"}},
    }
    uc_path = tmp_path / "use_case.json"
    uc_path.write_text(json.dumps(use_case), encoding="utf-8")
    out_dir = tmp_path / "out"

    monkeypatch.setattr(sys, "argv", ["compute.py", str(uc_path), str(out_dir)])
    main()

    result = json.loads((out_dir / "result.json").read_text(encoding="utf-8"))
    assert result["success"] is True
    assert result["outputs"]["mesh_required"] == 1
    assert os.path.exists(result["artifacts"]["params_yaml"])
