"""ComputeRunner feeds compute.py a snapshot of the use case taken when the runner is created,
so answers saved while compute starts up never leak into the run. It also keeps a registry of
running computes, so a module of a use case never has two runs writing to the same output files."""

import json
import os
import threading
import time
from datetime import datetime, timezone

import pytest

from app.engine import compute_runner
from app.engine.compute_runner import ComputeAlreadyRunning, ComputeRunner, is_compute_running
from app.models.questionnaire import QuestionnaireAnswers
from app.models.use_case import UseCase
from app.storage import json_store


def _run_to_completion(runner: ComputeRunner, done: threading.Event) -> None:
    runner.start()
    assert done.wait(timeout=60), "compute did not finish"


def _use_case(use_case_id: str = "reg") -> UseCase:
    now = datetime.now(timezone.utc).isoformat()
    return UseCase(id=use_case_id, name="Reg", created_at=now, updated_at=now,
                   answers=QuestionnaireAnswers(q_pipeline="inspection"),
                   module_answers={"grabber": {"q_grab_exposure": 1234}})


def _wait_until_idle(use_case_id: str, module_id: str) -> None:
    deadline = time.monotonic() + 60
    while is_compute_running(use_case_id, module_id):
        assert time.monotonic() < deadline, "compute is still registered as running"
        time.sleep(0.01)


def test_compute_reads_the_answers_from_when_the_runner_was_created(tmp_path, monkeypatch):
    monkeypatch.setattr(compute_runner, "_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(json_store, "_DATA_DIR", str(tmp_path))
    now = datetime.now(timezone.utc).isoformat()
    uc = UseCase(id="snap", name="Snap", created_at=now, updated_at=now,
                 answers=QuestionnaireAnswers(q_pipeline="inspection"),
                 module_answers={"grabber": {"q_grab_exposure": 1234}})
    json_store.save(uc)
    outcome, done = [], threading.Event()
    runner = ComputeRunner(uc, "grabber", lambda line: None,
                           lambda success, path: (outcome.append((success, path)), done.set()))

    # The partner saves new answers before the subprocess has read its input.
    uc.module_answers["grabber"]["q_grab_exposure"] = 9999
    json_store.save(uc)
    _run_to_completion(runner, done)

    [(success, result_path)] = outcome
    assert success
    with open(result_path, encoding="utf-8") as f:
        assert json.load(f)["outputs"]["exposure"] == 1234


def test_a_run_stays_registered_until_it_finishes_and_blocks_a_second_run(tmp_path, monkeypatch):
    monkeypatch.setattr(compute_runner, "_DATA_DIR", str(tmp_path))
    uc = _use_case()
    first_line, release, done = threading.Event(), threading.Event(), threading.Event()

    def hold_the_run(line: str) -> None:
        first_line.set()
        assert release.wait(timeout=60)

    runner = ComputeRunner(uc, "grabber", hold_the_run, lambda success, path: done.set())
    assert not is_compute_running(uc.id, "grabber")

    runner.start()
    assert first_line.wait(timeout=60)
    try:
        assert is_compute_running(uc.id, "grabber")
        assert not is_compute_running(uc.id, "localiser")
        assert not is_compute_running("another-use-case", "grabber")
        with pytest.raises(ComputeAlreadyRunning):
            ComputeRunner(uc, "grabber", lambda line: None, lambda success, path: None).start()
    finally:
        release.set()

    assert done.wait(timeout=60)
    assert not is_compute_running(uc.id, "grabber")


def test_a_listener_that_is_gone_neither_stops_the_run_nor_leaves_it_registered(tmp_path, monkeypatch):
    monkeypatch.setattr(compute_runner, "_DATA_DIR", str(tmp_path))
    uc = _use_case()

    def listener_is_gone(*args) -> None:
        raise RuntimeError("Internal C++ object already deleted")

    ComputeRunner(uc, "grabber", listener_is_gone, listener_is_gone).start()
    _wait_until_idle(uc.id, "grabber")

    assert os.path.exists(tmp_path / "reg" / "compute_outputs" / "grabber" / "result.json")
