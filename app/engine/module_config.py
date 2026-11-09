"""Resolve a module's numeric configuration questions to values, falling back to the schema defaults."""

from __future__ import annotations

import math

CONTROL_RATE_BLOCKER = "control rate (Hz) must be greater than 0"


def number_values(questions: list, answers: dict) -> dict:
    """{question id: float} for every number_float question; an unanswered one gets its schema default.

    Zero is a valid answer, so only a missing answer (None) falls back to the default.
    """
    values = {}
    for q in questions:
        if q.get("type") != "number_float":
            continue
        answer = answers.get(q["id"])
        values[q["id"]] = float(answer) if answer is not None else float(q["default"])
    return values


def valid_control_rate(value: float) -> bool:
    """A control rate must be finite and strictly positive, whatever the stored answer says."""
    return math.isfinite(value) and value > 0


def drop_invalid_control_rate(values: dict) -> dict:
    """``values`` without ``control_rate_hz`` when it is not a valid rate, so it is never written as output."""
    if valid_control_rate(values["control_rate_hz"]):
        return values
    return {k: v for k, v in values.items() if k != "control_rate_hz"}


def control_rate_blockers(questions: list, answers: dict) -> list:
    """The deploy blocker for an invalid control rate, as a list (empty when the rate is valid)."""
    rate = number_values(questions, answers)["control_rate_hz"]
    return [] if valid_control_rate(rate) else [CONTROL_RATE_BLOCKER]
