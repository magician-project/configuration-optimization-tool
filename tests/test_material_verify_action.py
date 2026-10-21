"""
Q5 materials: MAGICIAN-tested materials (metal/wood/plastic) only need a lightweight `verify` of the
existing pretrained classifier, while `other` still needs a full `retrain`.
"""

from datetime import datetime, timezone

import pytest

from app.engine import questionnaire_engine
from app.engine.questionnaire_engine import apply_impacts_to_modules, compute_impacts
from app.models.questionnaire import QuestionnaireAnswers
from app.models.use_case import UseCase

CLASSIFIERS = ("tactile_sensor", "vision_classifier")
RETRAIN_FLAG_ID = {"tactile_sensor": "flag_retrain", "vision_classifier": "flag_retrain_vision"}


def _answers(materials) -> QuestionnaireAnswers:
    return QuestionnaireAnswers(q3_additional_sensors=["tactile"], q5_materials=materials)


def _module(materials, module_id) -> dict:
    return compute_impacts(_answers(materials), module_answers={})["module_impacts"][module_id]


def _action_types(module: dict) -> list:
    return [i["action_type"] for i in module["impacts"]]


def _flags(module: dict) -> dict:
    # flag_cross_cutting is a separate, count-based flag, unrelated to the material rule.
    return {f["id"]: f["type"] for f in module["flags"] if f["id"] != "flag_cross_cutting"}


@pytest.mark.parametrize("module_id", CLASSIFIERS)
@pytest.mark.parametrize("material", ["metal", "wood", "plastic"])
def test_tested_material_gives_verify_impact_and_warning_flag(module_id, material):
    module = _module([material], module_id)

    assert _action_types(module) == ["verify"]
    flags = _flags(module)
    assert RETRAIN_FLAG_ID[module_id] not in flags
    assert list(flags.values()) == ["warning"]


@pytest.mark.parametrize("module_id", CLASSIFIERS)
def test_tested_material_impact_explains_why_it_is_lighter(module_id):
    impact = _module(["metal"], module_id)["impacts"][0]

    assert "MAGICIAN" in impact["what_changes"]


@pytest.mark.parametrize("module_id", CLASSIFIERS)
def test_other_material_keeps_retrain_impact_and_error_flag(module_id):
    module = _module(["other"], module_id)

    assert _action_types(module) == ["retrain"]
    assert _flags(module) == {RETRAIN_FLAG_ID[module_id]: "error"}


@pytest.mark.parametrize("module_id", CLASSIFIERS)
def test_mixed_choice_shows_only_retrain(module_id):
    module = _module(["metal", "other"], module_id)

    assert _action_types(module) == ["retrain"]
    assert _flags(module) == {RETRAIN_FLAG_ID[module_id]: "error"}


@pytest.mark.parametrize("module_id", CLASSIFIERS)
def test_retrain_text_names_only_materials_without_baseline(module_id):
    answers = QuestionnaireAnswers(
        q3_additional_sensors=["tactile"], q5_materials=["metal", "other"], q5_other_material="carbon fiber",
    )

    text = compute_impacts(answers, module_answers={})["module_impacts"][module_id]["impacts"][0]["what_changes"]

    assert "carbon fiber" in text
    assert "metal" not in text


@pytest.mark.parametrize("module_id", CLASSIFIERS)
def test_verify_flag_id_differs_from_retrain_flag_id(module_id):
    verify_ids = set(_flags(_module(["metal"], module_id)))
    retrain_ids = set(_flags(_module(["other"], module_id)))

    assert verify_ids.isdisjoint(retrain_ids)


def test_other_modules_keep_reconfigure_impacts_for_materials():
    result = compute_impacts(
        QuestionnaireAnswers(q_pipeline="both", q5_materials=["metal"]), module_answers={}
    )["module_impacts"]

    for module_id in ("orienteering_solver", "localiser"):
        assert _action_types(result[module_id]) == ["reconfigure"]


def test_lookup_table_allows_an_asymmetric_outcome(monkeypatch):
    monkeypatch.setattr(questionnaire_engine, "MATERIAL_ACTIONS", {
        "tactile_sensor": {"metal": "verify"},
        "vision_classifier": {"metal": "retrain"},
    })

    assert _action_types(_module(["metal"], "tactile_sensor")) == ["verify"]
    assert _action_types(_module(["metal"], "vision_classifier")) == ["retrain"]


def _use_case(materials) -> UseCase:
    now = datetime.now(timezone.utc).isoformat()
    uc = UseCase(id="test", name="Test", created_at=now, updated_at=now)
    uc.answers = _answers(materials)
    return uc


def _apply(uc: UseCase) -> None:
    apply_impacts_to_modules(uc, compute_impacts(uc.answers, module_answers={}))


@pytest.mark.parametrize("module_id", CLASSIFIERS)
def test_module_with_only_verify_impacts_still_needs_action(module_id):
    uc = _use_case(["metal"])

    _apply(uc)

    assert [i.action_type for i in uc.modules[module_id].impacts] == ["verify"]
    assert uc.modules[module_id].status == "needs_action"


@pytest.mark.parametrize("module_id", CLASSIFIERS)
def test_acknowledged_retrain_flag_does_not_carry_over_to_verify_flag(module_id):
    uc = _use_case(["other"])
    _apply(uc)
    for flag in uc.modules[module_id].flags:
        flag.acknowledged = True

    uc.answers = _answers(["metal"])
    _apply(uc)

    flags = [f for f in uc.modules[module_id].flags if f.id != "flag_cross_cutting"]
    assert [f.type for f in flags] == ["warning"]
    assert not any(f.acknowledged for f in flags)
