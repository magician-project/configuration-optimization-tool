"""
Tests for compute_default_modules(): the task-type -> default module set mapping.
"grinding" is a superset of "inspection" (there is no grind-only scenario), and an
unanswered task_type (None) falls back to "grinding" for backward compatibility
with use cases saved before this question existed.
"""

from app.engine.module_registry import compute_default_modules


def test_inspection_only_excludes_grinding_modules():
    modules = compute_default_modules("inspection")

    assert set(modules) == {"grabber", "localiser", "vision_classifier", "ergodic_control"}


def test_grinding_is_a_superset_of_inspection():
    inspection = set(compute_default_modules("inspection"))
    grinding = set(compute_default_modules("grinding"))

    assert inspection < grinding
    assert grinding == inspection | {"orienteering_solver", "motion_planning"}


def test_tactile_sensor_added_only_when_selected():
    without_tactile = compute_default_modules("inspection", additional_sensors=["distance"])
    with_tactile = compute_default_modules("inspection", additional_sensors=["tactile"])

    assert "tactile_sensor" not in without_tactile
    assert "tactile_sensor" in with_tactile


def test_unanswered_task_type_falls_back_to_grinding():
    assert compute_default_modules(None) == compute_default_modules("grinding")
