"""
Deploy of the IIT grinding runtime (ADR-0005): the gate over the three modules and the one
shared startup artifact they are combined into.
"""

from datetime import datetime, timezone

import pytest
import yaml

from app.engine.module_dependencies import validate_use_case
from app.engine.questionnaire_engine import apply_impacts_to_modules, compute_impacts
from app.engine.result_freshness import answers_fingerprint
from app.engine.runtime_deploy import (
    ARTIFACT_FILENAME, RUNTIME_MODULES, RUNTIME_NODE, build_runtime_params, deploy_runtime,
    runtime_deploy_blockers,
)
from app.engine.shared_parameters import answers_with_shared
from app.models.questionnaire import QuestionnaireAnswers
from app.models.use_case import ComputeResult, UseCase
from modules.cartesian_controller import compute as cartesian
from modules.dmp import compute as dmp
from modules.impedance_controller import compute as impedance

_COMPUTE = {"dmp": dmp, "cartesian_controller": cartesian, "impedance_controller": impedance}

_MODULE_ANSWERS = {
    "dmp": {
        "primitives": {
            "positive_dent": {"pose_path": "/p/pos_pose.npy", "wrench_path": "/p/pos_wrench.npy"},
            "negative_dent": {"pose_path": "/p/neg_pose.npy", "wrench_path": "/p/neg_wrench.npy"},
        },
        "tool_defect_offset_x_m": "0.01",
        "tool_defect_offset_y_m": "-0.02",
        "tool_defect_offset_z_m": "0.15",
    },
    "cartesian_controller": {"control_rate_hz": 500.0, "reach_duration_s": 12.0},
    "impedance_controller": {"measured_wrench_source": "grabber"},
}


def _compute(uc: UseCase, module_id: str) -> None:
    """Store a result the way a finished compute run does."""
    answers = {**uc.answers.model_dump(mode="json"), **answers_with_shared(module_id, uc.module_answers)}
    module = _COMPUTE[module_id]
    ms = uc.modules[module_id]
    ms.compute_result = ComputeResult(
        module_id=module_id, success=True, outputs=module.run(answers),
        deploy_blockers=module.deploy_blockers(answers), notes=module.notes(answers),
    )
    ms.computed_answers_fingerprint = answers_fingerprint(uc, module_id)
    ms.status = "computed"


def _use_case(compute=RUNTIME_MODULES, module_answers=None) -> UseCase:
    now = datetime.now(timezone.utc).isoformat()
    uc = UseCase(
        id="runtime", name="Runtime", created_at=now, updated_at=now,
        answers=QuestionnaireAnswers(
            q_pipeline="both", q3_additional_sensors=["tactile"], q8_defects=["positive_dent", "negative_dent"],
        ),
        module_answers=module_answers or {k: dict(v) for k, v in _MODULE_ANSWERS.items()},
    )
    apply_impacts_to_modules(uc, compute_impacts(uc.answers, uc.module_answers))
    for module_id in compute:
        _compute(uc, module_id)
    return uc


def test_a_complete_use_case_passes_the_gate():
    assert runtime_deploy_blockers(_use_case()) == []


@pytest.mark.parametrize("missing", RUNTIME_MODULES)
def test_a_module_that_is_not_computed_blocks_the_deploy(missing):
    uc = _use_case(compute=[m for m in RUNTIME_MODULES if m != missing])

    [reason] = runtime_deploy_blockers(uc)

    assert uc.modules[missing].module_name in reason
    assert "not computed" in reason


@pytest.mark.parametrize("module_id", RUNTIME_MODULES)
def test_a_module_that_is_out_of_date_blocks_the_deploy(module_id):
    uc = _use_case()
    uc.modules[module_id].computed_answers_fingerprint = "stale"

    [reason] = runtime_deploy_blockers(uc)

    assert uc.modules[module_id].module_name in reason
    assert "out of date" in reason


@pytest.mark.parametrize("module_id", RUNTIME_MODULES)
def test_a_deploy_blocker_of_any_module_blocks_the_deploy(module_id):
    uc = _use_case()
    uc.modules[module_id].compute_result.deploy_blockers = ["something is wrong"]

    [reason] = runtime_deploy_blockers(uc)

    assert uc.modules[module_id].module_name in reason
    assert "something is wrong" in reason


@pytest.mark.parametrize("module_id", RUNTIME_MODULES)
def test_a_result_that_never_evaluated_blockers_blocks_the_deploy(module_id):
    uc = _use_case()
    uc.modules[module_id].compute_result.deploy_blockers = None

    [reason] = runtime_deploy_blockers(uc)

    assert uc.modules[module_id].module_name in reason
    assert "Compute again" in reason


def test_an_open_capability_blocks_the_deploy():
    uc = _use_case(module_answers={**_MODULE_ANSWERS, "impedance_controller": {}})

    reasons = runtime_deploy_blockers(uc)

    assert reasons
    assert all(reason.startswith(uc.modules["impedance_controller"].module_name) for reason in reasons)
    assert any("choose a source" in reason for reason in reasons)
    assert validate_use_case(uc).capability_blockers


def test_a_module_outside_the_scope_blocks_the_deploy():
    uc = _use_case()
    uc.answers.q_pipeline = "inspection"
    apply_impacts_to_modules(uc, compute_impacts(uc.answers, uc.module_answers))

    reasons = runtime_deploy_blockers(uc)

    assert any("not in scope" in reason for reason in reasons)


def test_all_reasons_are_reported_at_once():
    uc = _use_case(compute=["dmp"])

    reasons = runtime_deploy_blockers(uc)

    assert len(reasons) == 2


def test_the_artifact_combines_the_parameters_of_all_three_modules():
    params = build_runtime_params(_use_case())[RUNTIME_NODE]["ros__parameters"]

    assert params["primitive_classes"] == "POSITIVE,NEGATIVE"
    assert params["primitive_positive_dent_pose_path"] == "/p/pos_pose.npy"
    assert params["tool_defect_offset_z_m"] == pytest.approx(0.15)
    assert params["reach_duration_s"] == 12.0
    assert params["unload_mode"] == "smooth retract"
    assert params["force_reference_scale"] == 1.0
    assert params["measured_wrench_topic"] == "/magician_grabber/wrench_sensed"


def test_the_control_rate_is_written_once_with_the_value_of_the_cartesian_controller():
    uc = _use_case()

    params = build_runtime_params(uc)[RUNTIME_NODE]["ros__parameters"]

    assert params["control_rate_hz"] == 500.0
    # Impedance reads the same value from its owner, so the single entry cannot contradict it.
    assert uc.modules["impedance_controller"].compute_result.outputs["control_rate_hz"] == 500.0


def test_every_parameter_of_every_module_is_in_the_artifact_exactly_once():
    uc = _use_case()
    expected = {key for module_id in RUNTIME_MODULES for key in uc.modules[module_id].compute_result.outputs}

    params = build_runtime_params(uc)[RUNTIME_NODE]["ros__parameters"]

    assert set(params) == expected


def test_a_parameter_that_two_modules_write_differently_is_an_error():
    uc = _use_case()
    uc.modules["dmp"].compute_result.outputs["reach_duration_s"] = 1.0

    with pytest.raises(ValueError, match="reach_duration_s"):
        build_runtime_params(uc)


def test_deploying_writes_the_params_yaml_and_returns_notes_only(tmp_path):
    uc = _use_case()

    deployment = deploy_runtime(uc, str(tmp_path))

    assert deployment.artifact_path == str(tmp_path / ARTIFACT_FILENAME)
    with open(deployment.artifact_path, encoding="utf-8") as f:
        assert yaml.safe_load(f) == build_runtime_params(uc)
    joined = "\n".join(deployment.notes)
    assert deployment.artifact_path in joined
    assert "Restart the IIT grinding runtime with this file" in joined
    assert "not verified with IIT" in joined


def test_the_artifact_holds_no_ros2_commands(tmp_path):
    deployment = deploy_runtime(_use_case(), str(tmp_path))

    text = (tmp_path / ARTIFACT_FILENAME).read_text(encoding="utf-8")
    assert "ros2" not in text
    assert "service" not in text.lower()
    assert not hasattr(deployment, "commands")


def test_the_modules_own_notes_are_kept_without_duplicates(tmp_path):
    deployment = deploy_runtime(_use_case(), str(tmp_path))

    assert len(deployment.notes) == len(set(deployment.notes))
    assert any("tool offset" in note for note in deployment.notes)


def test_a_blocked_deploy_writes_nothing(tmp_path):
    uc = _use_case(compute=["dmp"])

    with pytest.raises(ValueError):
        deploy_runtime(uc, str(tmp_path))

    assert list(tmp_path.iterdir()) == []


# --- UseCasePage: deploy from any of the three tiles -------------------------------------------

@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


class _CommandAdapter:
    """Fails the test when a deploy sends anything to ROS 2."""

    def apply_commands(self, module_id, commands):
        raise AssertionError("the runtime deploy must not send ROS 2 commands")


def _page(tmp_path, monkeypatch, uc):
    from app.storage import json_store
    from gui.pages import use_case_page

    monkeypatch.setattr(json_store, "_DATA_DIR", str(tmp_path))
    json_store.save(uc)
    warnings, infos = [], []
    monkeypatch.setattr(use_case_page.QMessageBox, "warning", lambda *args: warnings.append(args[1:]))
    monkeypatch.setattr(use_case_page.QMessageBox, "information", lambda *args: infos.append(args[1:]))
    monkeypatch.setattr(use_case_page, "get_adapter", lambda: _CommandAdapter())
    return use_case_page.UseCasePage(uc.id), warnings, infos


def _artifact(tmp_path) -> str:
    [path] = (tmp_path / "runtime" / "deploy_outputs" / "grinding_runtime").glob(ARTIFACT_FILENAME)
    return path.read_text(encoding="utf-8")


def test_deploying_from_each_tile_gives_the_same_artifact_and_deploys_all_three(qapp, tmp_path, monkeypatch):
    artifacts = []
    for module_id in RUNTIME_MODULES:
        folder = tmp_path / module_id
        folder.mkdir()
        page, warnings, infos = _page(folder, monkeypatch, _use_case())

        page._deploy_module(module_id)

        [(title, message)] = infos
        assert warnings == []
        assert "whole IIT grinding runtime" in message
        assert {m: page._use_case.modules[m].status for m in RUNTIME_MODULES} == dict.fromkeys(RUNTIME_MODULES, "deployed")
        assert all(page._use_case.modules[m].deployed_at for m in RUNTIME_MODULES)
        artifacts.append(_artifact(folder))

    assert len(set(artifacts)) == 1


def test_a_refused_deploy_names_the_reason_and_changes_nothing(qapp, tmp_path, monkeypatch):
    page, warnings, infos = _page(tmp_path, monkeypatch, _use_case(compute=["dmp", "cartesian_controller"]))

    page._deploy_module("dmp")

    [(title, message)] = warnings
    assert title == "Deployment blocked"
    assert "Impedance Controller is not computed" in message
    assert infos == []
    assert page._use_case.modules["dmp"].status == "computed"
    assert not (tmp_path / "runtime" / "deploy_outputs").exists()


def test_deploy_is_refused_from_any_tile_when_one_module_is_out_of_date(qapp, tmp_path, monkeypatch):
    page, warnings, _infos = _page(tmp_path, monkeypatch, _use_case())
    page._use_case.module_answers["cartesian_controller"]["reach_duration_s"] = 99.0

    page._deploy_module("impedance_controller")

    [(_title, message)] = warnings
    assert "out of date" in message


_EXTERNAL_WRENCH = {
    **_MODULE_ANSWERS,
    "impedance_controller": {"measured_wrench_source": "external", "measured_wrench_topic": "/partner/wrench"},
}


def test_deploy_is_refused_while_the_external_wrench_source_is_unnamed(qapp, tmp_path, monkeypatch):
    page, warnings, _infos = _page(tmp_path, monkeypatch, _use_case(module_answers=_EXTERNAL_WRENCH))

    page._deploy_module("dmp")

    [(_title, message)] = warnings
    assert "name the external source" in message


def test_deploy_is_allowed_once_the_external_wrench_source_is_named(qapp, tmp_path, monkeypatch):
    from app.models.use_case import ExternalSource

    uc = _use_case(module_answers=_EXTERNAL_WRENCH)
    uc.external_sources["measured_wrench"] = ExternalSource(source_name="Partner F/T")
    page, warnings, _infos = _page(tmp_path, monkeypatch, uc)

    page._deploy_module("dmp")

    assert warnings == []
    assert "/partner/wrench" in _artifact(tmp_path)


def test_the_tiles_of_the_runtime_say_that_deploy_covers_the_whole_runtime(qapp):
    from PySide6.QtWidgets import QLabel, QPushButton
    from gui.components.module_detail import ModuleDetail

    uc = _use_case()
    for module_id in RUNTIME_MODULES:
        dialog = ModuleDetail(uc.modules[module_id])

        buttons = [b.text() for b in dialog.findChildren(QPushButton)]
        labels = " ".join(w.text() for w in dialog.findChildren(QLabel))

        assert "Deploy IIT grinding runtime" in buttons
        assert "whole IIT grinding runtime" in labels
