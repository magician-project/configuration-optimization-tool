"""
Motion Planner — smoke tests

Covers default fallback vs. explicit zero handling for the Z-admittance
tuning fields, where 0.0 is a valid value (disables that term/bound) and
must not be silently replaced by the nonzero default.
"""

from modules.motion_planning.compute import run


def test_defaults_match_documented_section_4_values():
    outputs = run({})
    assert outputs["base_link"] == "base_link"
    assert outputs["ee_link"] == "tcp"
    assert outputs["ft_link"] == "tcp"
    assert outputs["integration_dt"] == 0.001
    assert outputs["proportional_gain"] == 1 / 3600
    assert outputs["integral_gain"] == 4.6
    assert outputs["integral_bound"] == 0.02
    assert outputs["integral_velocity_bound"] == 0.01


def test_explicit_zero_gains_and_bounds_are_preserved():
    outputs = run({
        "q_mp_proportional_gain": 0.0,
        "q_mp_integral_gain": 0.0,
        "q_mp_integral_bound": 0.0,
        "q_mp_integral_velocity_bound": 0.0,
    })
    assert outputs["proportional_gain"] == 0.0
    assert outputs["integral_gain"] == 0.0
    assert outputs["integral_bound"] == 0.0
    assert outputs["integral_velocity_bound"] == 0.0


def test_missing_gains_and_bounds_fall_back_to_defaults():
    outputs = run({})
    assert outputs["proportional_gain"] == 1 / 3600
    assert outputs["integral_gain"] == 4.6
    assert outputs["integral_bound"] == 0.02
    assert outputs["integral_velocity_bound"] == 0.01


def test_ft_link_defaults_to_ee_link_when_blank():
    outputs = run({"q_mp_ee_link": "custom_tcp"})
    assert outputs["ft_link"] == "custom_tcp"
