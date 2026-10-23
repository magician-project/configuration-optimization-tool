"""
Guards against the bug class caught in PR review: a schema question "id" that
doesn't match a QuestionnaireAnswers field name is silently dropped by
QuestionnaireAnswers(**pending_answers) (Pydantic ignores unknown kwargs by
default) — the GUI-selected value never reaches compute_impacts() or
compute_default_modules(), with no crash to signal it.
"""

import re
from pathlib import Path

from app.engine import schema as schema_module
from app.engine.module_registry import MODULES, readme_anchors
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


def _all_questions():
    from app.engine import schema

    questions = list(SCHEMA["questions"])
    for name in dir(schema):
        value = getattr(schema, name)
        if name.endswith("_CONFIG") and isinstance(value, list):
            questions.extend(value)
    return questions


_HELP_SECTIONS = {"What your choice changes", "Example"}
_MAX_TOOLTIP_WORDS = 40
_MAX_HELP_TEXT_WORDS = 150


def test_every_question_has_a_short_tooltip_summary():
    for q in _all_questions():
        words = len(q.get("tooltip", "").split())
        assert 0 < words <= _MAX_TOOLTIP_WORDS, f"{q['id']}: tooltip has {words} words"


def test_help_text_follows_the_shared_structure_and_length():
    for q in _all_questions():
        help_text = q.get("help_text")
        if help_text is None:
            continue
        headings = set(re.findall(r"^\*\*(.+?)\*\*$", help_text, flags=re.MULTILINE))
        assert "What your choice changes" in headings, f"{q['id']}: missing 'What your choice changes'"
        assert headings <= _HELP_SECTIONS, f"{q['id']}: unknown sections {headings - _HELP_SECTIONS}"
        assert len(help_text.split()) <= _MAX_HELP_TEXT_WORDS, f"{q['id']}: help_text too long"


def test_every_help_link_points_to_an_existing_module_readme_section():
    for q in _all_questions():
        link = q.get("help_link")
        if link is None:
            continue
        assert link["module"] in MODULES, f"{q['id']}: unknown module {link['module']!r}"
        assert link["anchor"] in readme_anchors(link["module"]), (
            f"{q['id']}: README of {link['module']} has no section {link['anchor']!r}"
        )


def test_tooltips_are_plain_language_without_cli_flags_or_internal_names():
    for q in _all_questions():
        tooltip = q.get("tooltip", "")
        assert not re.search(r"--\w+|GlobalConfig|common\.h", tooltip), (
            f"{q['id']}: technical detail belongs in the module README, not the tooltip"
        )
        jargon = re.search(r"\b(COT|TF frame|std_msgs|stdout|POSIX|softmax|AdamW|SHM)\b", tooltip)
        assert not jargon, f"{q['id']}: developer jargon {jargon.group(0)!r} in tooltip"


def test_implicitly_concatenated_schema_strings_keep_their_word_spacing():
    # "...writing" "files" silently becomes "writingfiles" in the GUI.
    source = (Path(schema_module.__file__)).read_text(encoding="utf-8")

    glued = re.findall(r'[^ \\n]"\r?\n\s+"[^ ]', source)

    assert glued == []


def test_pipeline_and_profit_questions_have_full_help():
    by_id = {q["id"]: q for q in SCHEMA["questions"]}

    for qid in ("q10_profit", "q_pipeline"):
        assert by_id[qid].get("help_text"), qid
        assert by_id[qid].get("help_link"), qid
    assert "external" in by_id["q_pipeline"]["help_text"].lower()


def test_ergodic_defaults_match_the_module_readme_and_compute_fallbacks():
    from app.engine.schema import ERGODIC_CONTROL_CONFIG

    by_id = {q["id"]: q for q in ERGODIC_CONTROL_CONFIG}
    expected = {
        "q_ergodic_sensor_offset": 0.05,
        "q_ergodic_kalman_process_noise": 0.1,
        "q_ergodic_kalman_measurement_noise": 0.5,
    }

    for qid, default in expected.items():
        # Fractional defaults need a float field; an integer spin box cannot hold them.
        assert by_id[qid]["type"] == "number_float", qid
        assert by_id[qid]["default"] == default, qid

