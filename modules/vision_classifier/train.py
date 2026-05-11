"""
Vision Classifier — train.py

Placeholder for the vision model training pipeline.
Replace the body of run_training() with real code once training data and
the training pipeline are available.
"""

from __future__ import annotations


def run_training(
    materials: list[str],
    output_dir: str,
) -> str:
    """
    Train the vision classifier on images of the given materials.

    Parameters
    ----------
    materials:   list of material labels (e.g. ["metal", "wood"])
    output_dir:  directory to write the trained model to

    Returns
    -------
    Path to the saved model file (.pth).
    """
    # TODO: implement real training pipeline
    # Steps:
    #   1. Load labeled image data for the given materials
    #   2. Fine-tune or retrain the vision defect detection model
    #   3. Save to output_dir/vision_model_{timestamp}.pth
    #   4. Return the saved model path
    raise NotImplementedError(
        "Vision classifier training pipeline is not yet implemented. "
        "Populate modules/vision_classifier/train.py with the real training code."
    )
