"""
Localiser — generate_config.py

Writes the ROS 2 parameter file the /localisation broadcaster reads at
startup. COT never writes the calibration transform itself — that comes
from the separate, operator-driven Registration procedure (see CONTEXT.md).
"""

import os
import yaml


def write_config(outputs: dict, output_dir: str) -> str:
    """
    Write localiser_params.yaml. Returns its path.
    """
    params: dict = {
        "setup": outputs.get("setup", ""),
        "database_file": outputs.get("database_file", ""),
        "mesh_path": outputs.get("mesh_path", ""),
        "robot_base_link": outputs.get("robot_base_link", ""),
        "robot_ee_link": outputs.get("robot_ee_link", ""),
        "mesh_link": outputs.get("mesh_link", ""),
        "mode": outputs.get("motion_mode", "static"),
    }

    if params["mode"] == "dynamic":
        params["slider_topic"] = outputs.get("slider_topic", "")
        params["slider_bias"] = outputs.get("slider_bias", 0.0)
        params["publish_rate_hz"] = outputs.get("publish_rate_hz", 30.0)

    doc = {"localisation": {"ros__parameters": params}}

    config_path = os.path.join(output_dir, "localiser_params.yaml")
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(doc, f, default_flow_style=False, sort_keys=False)

    return config_path
