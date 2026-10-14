"""
Tests for compute_default_modules(): the task-type -> default module set mapping.
"grinding" is a superset of "inspection" (there is no grind-only scenario), and an
unanswered task_type (None) falls back to "grinding" for backward compatibility
with use cases saved before this question existed.
"""

from app.engine.module_registry import MODULES, compute_default_modules, resolve_effective_overrides


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


def test_resolve_effective_overrides_follows_default_set_without_explicit_override():
    default_modules = compute_default_modules("inspection")

    effective = resolve_effective_overrides({}, default_modules)

    assert effective["grabber"] is True  # in the inspection default
    assert effective["orienteering_solver"] is False  # not in the inspection default


def test_resolve_effective_overrides_explicit_choice_always_wins():
    default_modules = compute_default_modules("inspection")
    module_overrides = {"grabber": False, "orienteering_solver": True}

    effective = resolve_effective_overrides(module_overrides, default_modules)

    assert effective["grabber"] is False  # explicitly off despite being in default
    assert effective["orienteering_solver"] is True  # explicitly on despite being out of default


def test_resolve_effective_overrides_covers_every_registered_module():
    effective = resolve_effective_overrides({}, [])
    assert set(effective) == set(MODULES)
