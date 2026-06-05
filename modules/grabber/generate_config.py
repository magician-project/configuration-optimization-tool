"""
Grabber — generate_config.py

Helpers that turn the flat outputs dict (produced by compute.py) into the
two deployment artifacts the operator needs to launch magician_grabber:

  • params.yaml  — ROS 2 parameter file for --ros-args --params-file
  • launch_args  — equivalent CLI argument string using parse_arguments flags
"""

import yaml
from typing import Optional


# Maximum exposure allowed without the --I_know_what_I_am_doing flag
MAX_EXPOSURE_US = 50_000

# Lighting mode → CLI flag mapping (from common.h parse_arguments)
_LIGHTING_FLAG: dict[str, Optional[str]] = {
    "rlight":  "--rlight",
    "dlight":  "--dlight",
    "tlight":  "--tlight",
    "trigger": "--trigger",
    "none":    None,
}


def generate_yaml(outputs: dict) -> str:
    """
    Build a ROS 2 parameter YAML string for magician_grabber.
    Usage:
        ros2 run rclcpp_magician_grabber magician_grabber \\
            --ros-args --params-file params.yaml
    """
    params: dict = {}

    # Hardware enable flags
    params["use_camera"]    = bool(outputs.get("use_camera", False))
    params["use_arduino"]   = bool(outputs.get("use_arduino", False))
    params["use_teensy"]    = bool(outputs.get("use_teensy", False))
    params["use_ati_force"] = bool(outputs.get("use_ati_force", False))
    params["stream_data"]   = bool(outputs.get("stream_data", False))
    params["simulate"]      = bool(outputs.get("simulate", False))

    # Camera settings
    if outputs.get("width"):
        params["width"] = int(outputs["width"])
    if outputs.get("height"):
        params["height"] = int(outputs["height"])
    if outputs.get("frame_rate"):
        params["frame_rate"] = float(outputs["frame_rate"])
    if outputs.get("exposure"):
        params["exposure"] = int(min(outputs["exposure"], MAX_EXPOSURE_US))
    if outputs.get("gain") is not None:
        params["gain"] = float(outputs["gain"])
    if outputs.get("black_level") is not None:
        params["black_level"] = float(outputs["black_level"])

    # ATI force sensor
    if outputs.get("ati_ip"):
        params["ati_ip"] = str(outputs["ati_ip"])
    if outputs.get("ati_port"):
        params["ati_port"] = int(outputs["ati_port"])

    # Serial paths
    if outputs.get("arduino_path"):
        params["arduino_path"] = str(outputs["arduino_path"])
    if outputs.get("teensy_path"):
        params["teensy_path"] = str(outputs["teensy_path"])

    # Shared memory streams
    if outputs.get("camera_stream_name"):
        params["camera_stream_name"] = str(outputs["camera_stream_name"])
    if outputs.get("tactile_stream_name"):
        params["tactile_stream_name"] = str(outputs["tactile_stream_name"])

    # Lighting
    params["manual_trigger_light"] = bool(outputs.get("manual_trigger_light", False))
    params["use_ram"]   = bool(outputs.get("use_ram", False))
    params["compress"]  = bool(outputs.get("compress", False))
    params["run_forever"] = bool(outputs.get("run_forever", True))
    if not outputs.get("run_forever", True) and outputs.get("max_time_seconds"):
        params["max_time_seconds"] = int(outputs["max_time_seconds"])

    doc = {"magician_grabber": {"ros__parameters": params}}
    return yaml.dump(doc, default_flow_style=False, sort_keys=False)


def generate_launch_args(outputs: dict) -> str:
    """
    Build a CLI argument string equivalent to the YAML, using the flag syntax
    accepted by parse_arguments() in common.h.
    """
    parts = ["magician_grabber"]

    if outputs.get("simulate"):
        parts.append("--simulate")
    if outputs.get("use_camera"):
        parts.append("--camera")
    if outputs.get("use_arduino"):
        parts.append("--distance")
    if outputs.get("use_teensy"):
        parts.append("--accelerometer")
    if outputs.get("use_ati_force"):
        parts.append("--force")
    if outputs.get("stream_data"):
        parts.append("--stream")

    if outputs.get("width") and outputs.get("height"):
        parts += ["--size", str(int(outputs["width"])), str(int(outputs["height"]))]

    if outputs.get("frame_rate"):
        parts += ["--fps", str(float(outputs["frame_rate"]))]

    if outputs.get("exposure"):
        exp = int(min(outputs["exposure"], MAX_EXPOSURE_US))
        parts += ["--exposure", str(exp)]

    if outputs.get("gain") is not None:
        parts += ["--gain", str(float(outputs["gain"]))]

    if outputs.get("black_level") is not None:
        parts += ["--blacklevel", str(float(outputs["black_level"]))]

    if outputs.get("ati_ip"):
        parts += ["--atiip", str(outputs["ati_ip"])]
    if outputs.get("ati_port"):
        parts += ["--atiport", str(int(outputs["ati_port"]))]

    if outputs.get("arduino_path"):
        parts += ["--arduino", str(outputs["arduino_path"])]
    if outputs.get("teensy_path"):
        parts += ["--teensy", str(outputs["teensy_path"])]

    if outputs.get("camera_stream_name"):
        parts += ["--camerastream", str(outputs["camera_stream_name"])]
    if outputs.get("tactile_stream_name"):
        parts += ["--tactilestream", str(outputs["tactile_stream_name"])]

    # Lighting mode
    lighting_flag = _LIGHTING_FLAG.get(str(outputs.get("lighting_mode", "none")))
    if lighting_flag:
        parts.append(lighting_flag)
    elif outputs.get("manual_trigger_light"):
        parts.append("--trigger")

    if outputs.get("use_ram"):
        parts.append("--ram")
    if outputs.get("compress"):
        parts.append("--compress")

    if outputs.get("run_forever", True):
        parts.append("--forever")
    elif outputs.get("max_time_seconds"):
        parts += ["--duration", str(int(outputs["max_time_seconds"]))]

    return " ".join(parts)
