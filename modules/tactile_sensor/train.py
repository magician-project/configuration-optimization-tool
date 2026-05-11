"""
Tactile Sensor — train.py

Placeholder for the actual CNN-LSTM training pipeline.
Replace the body of run_training() with the real training code once data
and the training pipeline are available.
"""

from __future__ import annotations
import os


def run_training(
    materials: list[str],
    defect_types: list[str],
    object_size: str,
    output_dir: str,
) -> str:
    """
    Train the tactile classifier on new material/defect-type data.

    Parameters
    ----------
    materials:    list of material labels (e.g. ["metal", "plastic"])
    defect_types: list of defect labels (e.g. ["dents", "dirt"])
    object_size:  size descriptor ("small" | "large" | "variable" | "unknown")
    output_dir:   directory to write the trained model checkpoint to

    Returns
    -------
    Path to the saved model checkpoint (.pth file).
    """
    # TODO: implement real training pipeline
    # Steps:
    #   1. Load labeled tactile data for the given materials and defect types
    #   2. Pre-process via Pre_calculations pipeline
    #   3. Train CNN-LSTM and LSTM-CNN ensemble
    #   4. Save checkpoint to output_dir/tactile_model_{timestamp}.pth
    #   5. Return the checkpoint path
    raise NotImplementedError(
        "Tactile classifier training pipeline is not yet implemented. "
        "Populate modules/tactile_sensor/train.py with the real training code."
    )
