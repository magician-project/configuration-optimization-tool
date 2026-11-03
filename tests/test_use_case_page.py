"""
Guards UseCasePage._finish_compute(): a compute that completes after its module has
left scope (pipeline changed while it was running) must not bring the module back.
Also guards UseCasePage._deploy_module(): result notes are shown, and pre-upgrade results
of modules that evaluate deploy blockers must be recomputed.
The out-of-date badge follows answer changes after compute, without blocking deploy.
Runs outlive their page: a run still going blocks a new compute on a reopened page, and a
"computing" status without a run is shown as failed.
"""

import json
import threading
import time

import pytest
from PySide6.QtWidgets import QApplication

from datetime import datetime, timezone

from app.engine import compute_runner
from app.engine.compute_runner import ComputeRunner, is_compute_running
from app.engine.questionnaire_engine import apply_impacts_to_modules, compute_impacts
from app.models.questionnaire import QuestionnaireAnswers
from app.models.use_case import ComputeResult, UseCase
from app.storage import json_store


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.mark.parametrize("pipeline, module_id, expected_status", [
    ("inspection", "orienteering_solver", "out_of_scope"),
    (None, "grabber", "not_assessed"),
])
def test_late_compute_result_is_discarded_for_module_without_scope(
    qapp, tmp_path, monkeypatch, pipeline, module_id, expected_status
):
    monkeypatch.setattr(json_store, "_DATA_DIR", str(tmp_path))
    now = datetime.now(timezone.utc).isoformat()
    uc = UseCase(id="late", name="Late", created_at=now, updated_at=now,
                 answers=QuestionnaireAnswers(q_pipeline=pipeline))
    apply_impacts_to_modules(uc, compute_impacts(uc.answers, module_answers={}))
    json_store.save(uc)
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps({"module_id": module_id, "success": True}))

    from gui.pages.use_case_page import UseCasePage
    page = UseCasePage("late")

    page._finish_compute(module_id, True, str(result_path))

    module = page._use_case.modules[module_id]
    assert module.status == expected_status
    assert module.compute_result is None


def _page_with_computed_module(tmp_path, monkeypatch, module_id, **result_fields):
    monkeypatch.setattr(json_store, "_DATA_DIR", str(tmp_path))
    now = datetime.now(timezone.utc).isoformat()
    uc = UseCase(id="deploy", name="Deploy", created_at=now, updated_at=now,
                 answers=QuestionnaireAnswers(q_pipeline="both", q3_additional_sensors=["tactile"]))
    apply_impacts_to_modules(uc, compute_impacts(uc.answers, module_answers={}))
    module = uc.modules[module_id]
    module.compute_result = ComputeResult(module_id=module_id, success=True, outputs={}, **result_fields)
    module.status = "computed"
    json_store.save(uc)

    from gui.pages import use_case_page
    warnings, infos = [], []
    monkeypatch.setattr(use_case_page.QMessageBox, "warning", lambda *args: warnings.append(args[1:]))
    monkeypatch.setattr(use_case_page.QMessageBox, "information", lambda *args: infos.append(args[1:]))
    monkeypatch.setattr(use_case_page, "get_adapter", lambda: _SucceedingAdapter())
    return use_case_page.UseCasePage("deploy"), warnings, infos


class _SucceedingAdapter:
    def apply_commands(self, module_id, commands):
        return {"success": True}


def test_deploy_shows_the_module_notes(qapp, tmp_path, monkeypatch):
    note = "defect class mapping not verified with module owner"
    page, warnings, infos = _page_with_computed_module(
        tmp_path, monkeypatch, "orienteering_solver", deploy_blockers=[], notes=[note],
    )

    page._deploy_module("orienteering_solver")

    assert warnings == []
    assert page._use_case.modules["orienteering_solver"].status == "deployed"
    [(_title, message)] = infos
    assert note in message


def test_deploy_without_notes_shows_no_notes_dialog(qapp, tmp_path, monkeypatch):
    page, warnings, infos = _page_with_computed_module(tmp_path, monkeypatch, "localiser", deploy_blockers=[])

    page._deploy_module("localiser")

    assert page._use_case.modules["localiser"].status == "deployed"
    assert (warnings, infos) == ([], [])


@pytest.mark.parametrize("module_id", ["tactile_sensor", "orienteering_solver", "ergodic_control"])
def test_q8_consumer_result_without_evaluated_blockers_must_be_recomputed(qapp, tmp_path, monkeypatch, module_id):
    page, warnings, _infos = _page_with_computed_module(tmp_path, monkeypatch, module_id)

    page._deploy_module(module_id)

    [(title, message)] = warnings
    assert title == "Cannot deploy"
    assert "Run Compute again" in message
    assert page._use_case.modules[module_id].status == "computed"


class _IdleRunner:
    def __init__(self, *args) -> None:
        pass

    def start(self) -> None:
        pass


class _SilentProgressDialog:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def show(self) -> None:
        pass

    def append_line(self, line) -> None:
        pass

    def on_done(self, success, result_path) -> None:
        pass


def _computing_page(tmp_path, monkeypatch, module_id):
    """A page on which compute of module_id was started but has not finished yet."""
    monkeypatch.setattr(json_store, "_DATA_DIR", str(tmp_path))
    now = datetime.now(timezone.utc).isoformat()
    uc = UseCase(id="fresh", name="Fresh", created_at=now, updated_at=now,
                 answers=QuestionnaireAnswers(q_pipeline="inspection"),
                 module_answers={module_id: {"q_example": "before"}})
    apply_impacts_to_modules(uc, compute_impacts(uc.answers, uc.module_answers))
    json_store.save(uc)

    from gui.pages import use_case_page
    monkeypatch.setattr(use_case_page, "ComputeRunner", _IdleRunner)
    monkeypatch.setattr(use_case_page, "ComputeProgressDialog", _SilentProgressDialog)
    page = use_case_page.UseCasePage("fresh")
    page._run_compute(module_id)
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps({"module_id": module_id, "success": True}))
    return page, str(result_path)


def _badge_visible(page, module_id) -> bool:
    from PySide6.QtWidgets import QLabel
    tile = page._module_grid.tile(module_id)
    return any(w.text() == "Out of date" and not w.isHidden() for w in tile.findChildren(QLabel))


def test_changing_an_answer_after_compute_shows_the_out_of_date_badge_and_reverting_clears_it(
    qapp, tmp_path, monkeypatch
):
    page, result_path = _computing_page(tmp_path, monkeypatch, "grabber")
    page._finish_compute("grabber", True, result_path)
    assert not _badge_visible(page, "grabber")

    page._on_module_config_changed("grabber", {"q_example": "after"})
    assert _badge_visible(page, "grabber")

    page._on_module_config_changed("grabber", {"q_example": "before"})
    assert not _badge_visible(page, "grabber")


def test_answers_changed_while_compute_runs_make_its_result_out_of_date(qapp, tmp_path, monkeypatch):
    page, result_path = _computing_page(tmp_path, monkeypatch, "grabber")

    page._on_module_config_changed("grabber", {"q_example": "after"})
    page._finish_compute("grabber", True, result_path)

    assert _badge_visible(page, "grabber")


def test_a_second_compute_is_refused_while_the_first_still_runs(qapp, tmp_path, monkeypatch):
    page, result_path = _computing_page(tmp_path, monkeypatch, "grabber")
    from gui.pages import use_case_page
    started, warnings = [], []
    monkeypatch.setattr(use_case_page, "ComputeRunner", lambda *args: started.append(args) or _IdleRunner())
    monkeypatch.setattr(use_case_page.QMessageBox, "warning", lambda *args: warnings.append(args[1:]))
    # Saving answers resets the "computing" status, so the status alone cannot guard against a rerun.
    page._on_module_config_changed("grabber", {"q_example": "after"})
    page._on_module_config_changed("grabber", {"q_example": "before"})

    page._run_compute("grabber")
    page._finish_compute("grabber", True, result_path)

    assert started == []
    [(title, _message)] = warnings
    assert title == "Compute already running"
    assert not _badge_visible(page, "grabber")


def _save_pipeline(page, pipeline) -> None:
    page._pending_answers = {**page._use_case.answers.model_dump(), "q_pipeline": pipeline}
    page._save_questionnaire()


@pytest.fixture
def orphan_run(tmp_path, monkeypatch):
    """Starts a real compute that keeps running until released, as if started by a page that is gone."""
    monkeypatch.setattr(compute_runner, "_DATA_DIR", str(tmp_path))
    release = threading.Event()
    started = []

    def start(use_case_id: str, module_id: str) -> threading.Event:
        uc = json_store.load(use_case_id)
        first_line = threading.Event()

        def hold_the_run(line: str) -> None:
            first_line.set()
            release.wait(timeout=60)

        runner = ComputeRunner(uc, module_id, hold_the_run, lambda success, path: None)
        runner.start()
        started.append((use_case_id, module_id))
        assert first_line.wait(timeout=60)
        return release

    yield start
    release.set()
    for use_case_id, module_id in started:
        deadline = datetime.now(timezone.utc).timestamp() + 60
        while is_compute_running(use_case_id, module_id):
            assert datetime.now(timezone.utc).timestamp() < deadline
            threading.Event().wait(0.01)


def test_a_compute_still_running_from_an_earlier_page_blocks_compute_on_a_reopened_page(
    qapp, tmp_path, monkeypatch, orphan_run
):
    page, _result_path = _computing_page(tmp_path, monkeypatch, "grabber")
    orphan_run("fresh", "grabber")
    from gui.pages import use_case_page
    started, warnings = [], []
    monkeypatch.setattr(use_case_page, "ComputeRunner", lambda *args: started.append(args) or _IdleRunner())
    monkeypatch.setattr(use_case_page.QMessageBox, "warning", lambda *args: warnings.append(args[1:]))

    reopened = use_case_page.UseCasePage("fresh")
    reopened._run_compute("grabber")

    assert started == []
    [(title, _message)] = warnings
    assert title == "Compute already running"


def test_reopening_a_use_case_whose_compute_is_gone_shows_compute_failed(qapp, tmp_path, monkeypatch):
    _computing_page(tmp_path, monkeypatch, "grabber")

    from gui.pages.use_case_page import UseCasePage
    reopened = UseCasePage("fresh")

    assert reopened._use_case.modules["grabber"].status == "compute_failed"
    assert json_store.load("fresh").modules["grabber"].status == "compute_failed"


def test_reopening_a_use_case_whose_compute_still_runs_keeps_it_computing(
    qapp, tmp_path, monkeypatch, orphan_run
):
    _computing_page(tmp_path, monkeypatch, "grabber")
    orphan_run("fresh", "grabber")

    from gui.pages.use_case_page import UseCasePage
    reopened = UseCasePage("fresh")

    assert reopened._use_case.modules["grabber"].status == "computing"


def _wait_for_status(page, module_id: str, status: str) -> None:
    deadline = time.monotonic() + 30
    while page._use_case.modules[module_id].status != status:
        assert time.monotonic() < deadline, f"{module_id} never reached {status}"
        QApplication.processEvents()
        time.sleep(0.01)


def test_a_reopened_page_recovers_when_the_compute_it_found_running_ends(
    qapp, tmp_path, monkeypatch, orphan_run
):
    from gui.pages import use_case_page
    monkeypatch.setattr(use_case_page.UseCasePage, "_ORPHAN_POLL_MS", 10)
    _computing_page(tmp_path, monkeypatch, "grabber")
    release = orphan_run("fresh", "grabber")
    reopened = use_case_page.UseCasePage("fresh")
    assert reopened._use_case.modules["grabber"].status == "computing"

    release.set()
    _wait_for_status(reopened, "grabber", "compute_failed")

    from PySide6.QtWidgets import QLabel
    tile_texts = [w.text() for w in reopened._module_grid.tile("grabber").findChildren(QLabel)]
    assert "Compute failed" in tile_texts
    assert "Run Compute again" in reopened._banner.text()
    assert json_store.load("fresh").modules["grabber"].status == "compute_failed"


def test_the_recovery_leaves_a_compute_of_this_page_alone(qapp, tmp_path, monkeypatch):
    page, _result_path = _computing_page(tmp_path, monkeypatch, "grabber")

    page._recover_orphaned_computes()

    assert page._use_case.modules["grabber"].status == "computing"


# A new run overwrites the artifact files of the kept result in compute_outputs/<module>/,
# so once it starts, that result can no longer be trusted, whatever happens to the run.
def test_a_failed_recompute_leaves_the_previous_result_out_of_date(qapp, tmp_path, monkeypatch):
    page, result_path = _computing_page(tmp_path, monkeypatch, "grabber")
    page._finish_compute("grabber", True, result_path)

    page._run_compute("grabber")
    page._finish_compute("grabber", False, None)

    assert page._use_case.modules["grabber"].compute_result is not None
    assert _badge_visible(page, "grabber")


def test_a_discarded_recompute_leaves_the_previous_result_out_of_date_after_reverting(
    qapp, tmp_path, monkeypatch
):
    page, result_path = _computing_page(tmp_path, monkeypatch, "grabber")
    page._finish_compute("grabber", True, result_path)

    page._run_compute("grabber")
    _save_pipeline(page, None)
    page._finish_compute("grabber", True, result_path)
    _save_pipeline(page, "inspection")

    assert _badge_visible(page, "grabber")


def test_the_fingerprint_survives_reloading_the_use_case(qapp, tmp_path, monkeypatch):
    page, result_path = _computing_page(tmp_path, monkeypatch, "grabber")
    page._finish_compute("grabber", True, result_path)

    from gui.pages.use_case_page import UseCasePage
    reloaded = UseCasePage("fresh")

    assert reloaded._use_case.modules["grabber"].computed_answers_fingerprint is not None
    assert not _badge_visible(reloaded, "grabber")


def test_an_out_of_date_result_does_not_block_deploy_of_existing_modules(qapp, tmp_path, monkeypatch):
    page, warnings, _infos = _page_with_computed_module(tmp_path, monkeypatch, "localiser", deploy_blockers=[])
    assert _badge_visible(page, "localiser")

    page._deploy_module("localiser")

    assert warnings == []
    assert page._use_case.modules["localiser"].status == "deployed"
