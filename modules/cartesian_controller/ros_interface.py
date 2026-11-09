"""
Cartesian Controller — ros_interface.py

The Cartesian Controller is part of the IIT grinding runtime, which is configured once at
startup. COT does not set its parameters live, so there is nothing to fire here: the commands
are notes only. The real deploy goes through the runtime (ticket 13).
"""

from typing import List

from app.models.use_case import ROS2Command


def get_commands(outputs: dict) -> List[ROS2Command]:
    return [
        ROS2Command(
            type="note",
            param_name="cartesian_controller",
            value="startup configuration only: COT does not set Cartesian Controller parameters on the running node",
        ),
    ]
