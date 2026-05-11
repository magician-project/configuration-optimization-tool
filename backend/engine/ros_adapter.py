import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ROSAdapter:
    def deploy_module(self, module_id: str, impacts: list) -> Dict[str, Any]:
        raise NotImplementedError


class MockROSAdapter(ROSAdapter):
    def deploy_module(self, module_id: str, impacts: list) -> Dict[str, Any]:
        logger.info("[MOCK ROS] Deploying module: %s (%d impacts)", module_id, len(impacts))
        return {
            "success": True,
            "module_id": module_id,
            "message": f"Mock deployment of '{module_id}' acknowledged by ROS framework.",
        }


def get_adapter() -> ROSAdapter:
    import os
    if os.getenv("ROS_MOCK", "true").lower() != "false":
        return MockROSAdapter()
    raise NotImplementedError("Real ROS adapter not yet implemented. Set ROS_MOCK=false only when ready.")
