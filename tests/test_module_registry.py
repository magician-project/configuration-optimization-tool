"""
Tests for compute_default_modules(): the pipeline selection -> default module set mapping.
An unanswered pipeline (None) falls back to "both" for backward compatibility with use
cases saved before this question existed.
"""

from app.engine.module_registry import compute_default_modules

_INSPECTION = {"grabber", "vision_classifier", "ergodic_control"}
_SHARED = {"localiser", "motion_planning"}


def test_inspection_excludes_grinding_modules():
    assert set(compute_default_modules("inspection")) == _INSPECTION | _SHARED


def test_grinding_excludes_inspection_modules():
    assert set(compute_default_modules("grinding")) == {"orienteering_solver"} | _SHARED


def test_both_combines_inspection_and_grinding():
    assert set(compute_default_modules("both")) == _INSPECTION | {"orienteering_solver"} | _SHARED


def test_tactile_sensor_added_only_when_selected():
    without_tactile = compute_default_modules("inspection", additional_sensors=["distance"])
    with_tactile = compute_default_modules("inspection", additional_sensors=["tactile"])

    assert "tactile_sensor" not in without_tactile
    assert "tactile_sensor" in with_tactile


def test_tactile_sensor_ignored_for_grinding_only():
    assert "tactile_sensor" not in compute_default_modules("grinding", additional_sensors=["tactile"])


def test_unanswered_pipeline_falls_back_to_both():
    assert compute_default_modules(None) == compute_default_modules("both")
