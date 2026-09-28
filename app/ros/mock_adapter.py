"""
mock_adapter.py — development/testing adapter (no ROS 2 required).
"""

import logging
from typing import Any, Dict, List
from app.models.use_case import ROS2Command

logger = logging.getLogger(__name__)


class MockROS2Adapter:
    """Logs the commands that would be sent to ROS 2 without executing them."""

    def apply_commands(self, module_id: str, commands: List[ROS2Command]) -> Dict[str, Any]:
        logger.info("[MOCK ROS2] Module: %s — %d command(s)", module_id, len(commands))
        for cmd in commands:
            if cmd.type == "param":
                logger.info(
                    "  ros2 param set %s %s %r", cmd.node, cmd.param_name, cmd.value
                )
            elif cmd.type == "service":
                logger.info(
                    "  ros2 service call %s %s %r", cmd.service, cmd.service_type, cmd.request_args
                )
            elif cmd.type == "note":
                logger.info("  [NOTE] %s: %s", cmd.param_name, cmd.value)
        return {
            "success": True,
            "module_id": module_id,
            "commands_sent": len(commands),
            "message": f"[MOCK] {len(commands)} command(s) logged for '{module_id}'.",
        }
