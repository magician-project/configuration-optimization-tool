"""ComputeRunner feeds compute.py a snapshot of the use case taken when the runner is created,
so answers saved while compute starts up never leak into the run."""

import json
import threading
from datetime import datetime, timezone

from app.engine import compute_runner
from app.engine.compute_runner import ComputeRunner
from app.models.questionnaire import QuestionnaireAnswers
from app.models.use_case import UseCase
from app.storage import json_store


def _run_to_completion(runner: ComputeRunner, done: threading.Event) -> None:
    runner.start()
    assert done.wait(timeout=60), "compute did not finish"


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
