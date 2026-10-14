"""
Guards against the bug class caught in PR review: a schema question "id" that
doesn't match a QuestionnaireAnswers field name is silently dropped by
QuestionnaireAnswers(**pending_answers) (Pydantic ignores unknown kwargs by
default) — the GUI-selected value never reaches compute_impacts() or
compute_default_modules(), with no crash to signal it.
"""

from app.engine.schema import SCHEMA
from app.models.questionnaire import QuestionnaireAnswers

# Module-specific config lives in UseCase.module_answers[module_id], not on
# QuestionnaireAnswers (see app/models/questionnaire.py notes).
_MODULE_CONFIG_PREFIXES = ("q_clf_", "q_grab_", "q_ergodic_")


def _question_ids(schema):
    ids = []
    for q in schema["questions"]:
        ids.append(q["id"])
        follow_up = q.get("follow_up")
        if follow_up:
            ids.append(follow_up["question"]["id"])
    return ids


def test_every_general_question_id_has_a_matching_questionnaire_answers_field():
    fields = QuestionnaireAnswers.model_fields

    for qid in _question_ids(SCHEMA):
        if qid.startswith(_MODULE_CONFIG_PREFIXES):
            continue
        assert qid in fields, (
            f"Schema question id {qid!r} has no matching QuestionnaireAnswers field — "
            "its answer would be silently discarded on save."
        )
