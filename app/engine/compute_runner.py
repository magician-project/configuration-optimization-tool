"""
compute_runner.py

Spawns a module's compute.py as a child subprocess and streams its stdout/stderr
back to the caller via a callback. This keeps the GUI responsive.

Usage from the GUI (PySide6):

    from app.engine.compute_runner import ComputeRunner

    def on_line(text: str): ...
    def on_done(success: bool, result_path: str | None): ...

    runner = ComputeRunner(use_case, "vision_classifier", on_line, on_done)
    runner.start()   # non-blocking — runs in a QThread internally

The runner writes result.json to:
    data/use_cases/{use_case_id}/compute_outputs/{module_id}/result.json
"""

from __future__ import annotations

import os
import sys
import json
import subprocess
import threading
import logging
from typing import Callable, Optional

from app.models.use_case import UseCase

logger = logging.getLogger(__name__)

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DATA_DIR = os.path.join(_REPO_ROOT, "data", "use_cases")


def _use_case_json_path(use_case_id: str) -> str:
    safe = "".join(c for c in use_case_id if c.isalnum() or c == "-")
    return os.path.join(_DATA_DIR, safe, "use_case.json")


def _output_dir(use_case_id: str, module_id: str) -> str:
    safe_uc = "".join(c for c in use_case_id if c.isalnum() or c == "-")
    safe_mod = "".join(c for c in module_id if c.isalnum() or c in "-_")
    return os.path.join(_DATA_DIR, safe_uc, "compute_outputs", safe_mod)


class ComputeRunner:
    """
    Runs a module's compute.py in a background thread.

    Parameters
    ----------
    use_case:    UseCase object (used to locate use_case.json on disk)
    module_id:   one of the MODULES keys (e.g. "vision_classifier")
    on_line:     called with each line of stdout/stderr from the subprocess
    on_done:     called when the subprocess exits;
                 args: (success: bool, result_json_path: str | None)
    """

    def __init__(
        self,
        use_case: UseCase,
        module_id: str,
        on_line: Callable[[str], None],
        on_done: Callable[[bool, Optional[str]], None],
    ) -> None:
        self._use_case = use_case
        self._module_id = module_id
        self._on_line = on_line
        self._on_done = on_done
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the compute subprocess in a background thread (non-blocking)."""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        uc_json = _use_case_json_path(self._use_case.id)
        out_dir = _output_dir(self._use_case.id, self._module_id)

        if not os.path.exists(uc_json):
            self._on_line(f"[error] use_case.json not found at {uc_json}")
            self._on_done(False, None)
            return

        module_dotted = f"modules.{self._module_id}.compute"
        cmd = [sys.executable, "-m", module_dotted, uc_json, out_dir]

        self._on_line(f"[compute_runner] Starting: {' '.join(cmd)}")

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=_REPO_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
            )

            for line in proc.stdout:  # type: ignore[union-attr]
                self._on_line(line.rstrip())

            proc.wait()
            success = proc.returncode == 0

            result_path = os.path.join(out_dir, "result.json")
            if success and os.path.exists(result_path):
                self._on_done(True, result_path)
            else:
                msg = (
                    f"[compute_runner] Subprocess exited with code {proc.returncode}"
                    if not success
                    else f"[compute_runner] result.json not found at {result_path}"
                )
                self._on_line(msg)
                self._on_done(False, None)

        except Exception as exc:
            logger.exception("Compute runner failed for %s", self._module_id)
            self._on_line(f"[compute_runner] Exception: {exc}")
            self._on_done(False, None)
