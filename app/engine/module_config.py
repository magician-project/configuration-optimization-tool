"""Resolve a module's numeric configuration questions to values, falling back to the schema defaults."""

from __future__ import annotations


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
