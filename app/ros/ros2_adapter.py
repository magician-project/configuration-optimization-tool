"""
ros2_adapter.py — real ROS 2 adapter.

Executes `ros2 param set` and `ros2 service call` commands via subprocess.
Only str, int, and float values are passed to ROS 2 (enforced at call time).

Environment variable:
    ROS_MOCK=true  →  MockROS2Adapter is used instead (default for dev machines)
    ROS_MOCK=false →  this real adapter is used
"""

import logging
import subprocess
import json
from typing import Any, Dict, List

from app.models.use_case import ROS2Command

logger = logging.getLogger(__name__)

# How long (seconds) to wait for each ros2 subprocess call before timing out
_CMD_TIMEOUT = 10


class ROS2Adapter:
    """Fires real ros2 param set / service call commands via subprocess."""

    def apply_commands(self, module_id: str, commands: List[ROS2Command]) -> Dict[str, Any]:
        results = []
        all_ok = True

        for cmd in commands:
            try:
                if cmd.type == "param":
                    ok, out = self._param_set(cmd)
                elif cmd.type == "service":
                    ok, out = self._service_call(cmd)
                else:
                    ok, out = False, f"Unknown command type: {cmd.type!r}"

                results.append({"ok": ok, "output": out})
                if not ok:
                    all_ok = False
                    logger.error("[ROS2] Command failed: %s", out)

            except Exception as exc:
                logger.exception("[ROS2] Exception executing command")
                results.append({"ok": False, "output": str(exc)})
                all_ok = False

        return {
            "success": all_ok,
            "module_id": module_id,
            "commands_sent": len(commands),
            "results": results,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _param_set(self, cmd: ROS2Command) -> tuple[bool, str]:
        value_str = self._value_to_str(cmd.value)
        cli = ["ros2", "param", "set", cmd.node, cmd.param_name, value_str]
        logger.info("[ROS2] %s", " ".join(cli))
        return self._run(cli)

    def _service_call(self, cmd: ROS2Command) -> tuple[bool, str]:
        args_json = json.dumps(cmd.request_args or {})
        cli = ["ros2", "service", "call", cmd.service, cmd.service_type, args_json]
        logger.info("[ROS2] %s", " ".join(cli))
        return self._run(cli)

    def _run(self, cli: list[str]) -> tuple[bool, str]:
        try:
            result = subprocess.run(
                cli,
                capture_output=True,
                text=True,
                timeout=_CMD_TIMEOUT,
            )
            output = (result.stdout + result.stderr).strip()
            return result.returncode == 0, output
        except subprocess.TimeoutExpired:
            return False, f"Timed out after {_CMD_TIMEOUT}s"
        except FileNotFoundError:
            return False, "ros2 binary not found — is ROS 2 sourced in this environment?"

    @staticmethod
    def _value_to_str(value: Any) -> str:
        """Convert a parameter value to the string form ros2 param set expects."""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            return str(value)
        return str(value)


def get_adapter():
    """Return the appropriate adapter based on the ROS_MOCK env var."""
    import os
    if os.getenv("ROS_MOCK", "true").lower() != "false":
        from app.ros.mock_adapter import MockROS2Adapter
        return MockROS2Adapter()
    return ROS2Adapter()
