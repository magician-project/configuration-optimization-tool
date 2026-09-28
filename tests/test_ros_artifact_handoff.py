import pytest

from app.models.use_case import ComputeResult
from modules.ergodic_control.ros_interface import get_commands as ergodic_commands
from modules.grabber.ros_interface import get_commands as grabber_commands
from modules.vision_classifier.ros_interface import get_commands as vision_commands


@pytest.mark.parametrize(
    ("module_id", "artifacts", "get_commands", "expected_notes"),
    [
        (
            "grabber",
            {"params_yaml": "grabber/params.yaml", "launch_args": "grabber/launch_args.txt"},
            grabber_commands,
            {
                "params_yaml_path": "grabber/params.yaml",
                "launch_args_path": "grabber/launch_args.txt",
            },
        ),
        (
            "vision_classifier",
            {"training_config": "vision/training_config.json", "live_config": "vision/live_config.json"},
            vision_commands,
            {"live_config_path": "vision/live_config.json"},
        ),
        (
            "ergodic_control",
            {"trajectory_config": "ergodic/trajectory_config.json", "kalman_config": "ergodic/kalman_config.json"},
            ergodic_commands,
            {
                "trajectory_config_path": "ergodic/trajectory_config.json",
                "kalman_config_path": "ergodic/kalman_config.json",
            },
        ),
    ],
)
def test_compute_artifact_paths_reach_ros_interface(
    module_id, artifacts, get_commands, expected_notes
):
    result = ComputeResult(
        module_id=module_id,
        success=True,
        outputs={"example_value": "preserved"},
        artifacts=artifacts,
    )

    commands = get_commands(result.interface_outputs())
    notes = {command.param_name: command.value for command in commands if command.type == "note"}

    assert notes == expected_notes
    assert result.interface_outputs()["example_value"] == "preserved"