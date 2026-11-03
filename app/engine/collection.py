"""
Collection question type — one row of item fields per selected option of a driver.

A collection question lives in a module's *_CONFIG and names its driver explicitly:
a checkbox question from the general questionnaire, optionally filtered to the
options the module supports. Its answer is stored as
``module_answers[<module>][<id>][<option>][<item field>]``. Values of an option
that is no longer selected are kept, so they return on reselection, but they are
ignored: never shown, validated or written to compute output.
"""

from __future__ import annotations

from app.engine.schema import SCHEMA


def driver_question(question: dict) -> dict:
    """The general questionnaire checkbox question that drives this collection."""
    field = question["driver"]["field"]
    for q in SCHEMA["questions"]:
        if q["id"] == field:
            if q.get("type") != "checkbox":
                raise ValueError(f"{question['id']}: driver {field!r} must be a checkbox question")
            return q
    raise ValueError(f"{question['id']}: driver {field!r} is not a general questionnaire question")


def driver_answers(questions: list[dict], general_answers: dict) -> dict:
    """The general questionnaire answers a module form may read: only its collections' drivers."""
    fields = {q["driver"]["field"] for q in questions if q.get("type") == "collection"}
    return {field: general_answers[field] for field in fields if field in general_answers}


def collection_options(question: dict) -> list[dict]:
    """The driver options (``{"value", "label"}``) this collection allows, in driver order."""
    options = driver_question(question).get("options", [])
    allowed = question["driver"].get("options")
    if allowed is None:
        return list(options)
    unknown = set(allowed) - {o["value"] for o in options}
    if unknown:
        raise ValueError(f"{question['id']}: driver has no options {sorted(unknown)}")
    return [o for o in options if o["value"] in allowed]


def selected_options(question: dict, drivers: dict) -> list[str]:
    """The allowed driver options that are currently selected in ``drivers``, in driver order."""
    selected = drivers.get(question["driver"]["field"]) or []
    return [o["value"] for o in collection_options(question) if o["value"] in selected]


def active_items(question: dict, value: dict | None, drivers: dict) -> dict:
    """The stored items of the selected options only; a selected option without answers maps to ``{}``."""
    value = value or {}
    return {option: dict(value.get(option) or {}) for option in selected_options(question, drivers)}
