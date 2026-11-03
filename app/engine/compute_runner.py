"""
compute_runner.py

Spawns a module's compute.py as a child subprocess and streams its stdout/stderr
back to the caller via a callback. This keeps the GUI responsive.

Usage from the GUI (PySide6):

    from app.engine.compute_runner import ComputeRunner

    def on_line(text: str): ...
    def on_done(success: bool, result_path: str | None): ...

    runner = ComputeRunner(use_case, "vision_classifier", on_line, on_done)
    runner.start()   # non-blocking — runs in a background thread

The runner snapshots the use case when it is created and gives compute.py that
snapshot, not the live use_case.json: answers saved while compute starts up must
not leak into the run (its answers fingerprint is taken from the same snapshot).

The runner writes result.json to:
    data/use_cases/{use_case_id}/compute_outputs/{module_id}/result.json
"""

from __future__ import annotations

import os
import sys
import json
import subprocess
import tempfile
import threading
import logging
from typing import Callable, Optional

from app.models.use_case import UseCase

logger = logging.getLogger(__name__)

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DATA_DIR = os.path.join(_REPO_ROOT, "data", "use_cases")


def _output_dir(use_case_id: str, module_id: str) -> str:
    safe_uc = "".join(c for c in use_case_id if c.isalnum() or c == "-")
    safe_mod = "".join(c for c in module_id if c.isalnum() or c in "-_")
    return os.path.join(_DATA_DIR, safe_uc, "compute_outputs", safe_mod)


class ComputeRunner:
    """
    Runs a module's compute.py in a background thread.

    Parameters
    ----------
    use_case:    UseCase object; snapshotted here, later changes do not reach compute.py
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
        self._use_case_id = use_case.id
        self._snapshot = json.dumps(use_case.model_dump(mode="json"), indent=2)
        self._module_id = module_id
        self._on_line = on_line
        self._on_done = on_done
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the compute subprocess in a background thread (non-blocking)."""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        out_dir = _output_dir(self._use_case_id, self._module_id)
        input_path: Optional[str] = None

        # Force the child process to write UTF-8 to stdout/stderr regardless of the
        # platform's default console codepage (e.g. cp1252 on Windows). Without this,
        # non-ASCII characters printed by a module's compute.py (em dashes, accented
        # characters, etc.) can be encoded in a way that isn't valid UTF-8, which then
        # raises a UnicodeDecodeError when we read the pipe below and crashes the run.
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        try:
            fd, input_path = tempfile.mkstemp(prefix=f"cot_{self._module_id}_", suffix=".json")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(self._snapshot)

            module_dotted = f"modules.{self._module_id}.compute"
            cmd = [sys.executable, "-m", module_dotted, input_path, out_dir]
            self._on_line(f"[compute_runner] Starting: {' '.join(cmd)}")

            proc = subprocess.Popen(
                cmd,
                cwd=_REPO_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
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
        finally:
            if input_path is not None:
                try:
                    os.remove(input_path)
                except OSError:
                    logger.warning("Could not remove compute input snapshot %s", input_path)
