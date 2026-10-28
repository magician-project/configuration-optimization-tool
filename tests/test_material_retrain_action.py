"""
Q5 materials: every selected material (also the MAGICIAN-tested metal/wood/plastic) needs a full `retrain`
of the tactile and vision classifiers, because object shapes/geometry can differ from the baseline.
"""

from datetime import datetime, timezone

import pytest

from app.engine.questionnaire_engine import apply_impacts_to_modules, compute_impacts
from app.models.questionnaire import QuestionnaireAnswers
from app.models.use_case import UseCase

CLASSIFIERS = ("tactile_sensor", "vision_classifier")
RETRAIN_FLAG_ID = {"tactile_sensor": "flag_retrain", "vision_classifier": "flag_retrain_vision"}


def _answers(materials, **extra) -> QuestionnaireAnswers:
    return QuestionnaireAnswers(
        q_pipeline="both", q3_additional_sensors=["tactile"], q5_materials=materials, **extra
    )


def _module(materials, module_id, **extra) -> dict:
    return compute_impacts(_answers(materials, **extra), module_answers={})["module_impacts"][module_id]


def _action_types(module: dict) -> list:
    return [i["action_type"] for i in module["impacts"]]


def _flags(module: dict) -> dict:
    # flag_cross_cutting is a separate, count-based flag, unrelated to the material rule.
    return {f["id"]: f["type"] for f in module["flags"] if f["id"] != "flag_cross_cutting"}


@pytest.mark.parametrize("module_id", CLASSIFIERS)
@pytest.mark.parametrize("material", ["metal", "wood", "plastic", "other"])
def test_every_material_gives_retrain_impact_and_error_flag(module_id, material):
    module = _module([material], module_id)

    assert _action_types(module) == ["retrain"]
    assert _flags(module) == {RETRAIN_FLAG_ID[module_id]: "error"}


@pytest.mark.parametrize("module_id", CLASSIFIERS)
def test_mixed_choice_gives_a_single_retrain_impact(module_id):
    module = _module(["metal", "other"], module_id)

    assert _action_types(module) == ["retrain"]
    assert _flags(module) == {RETRAIN_FLAG_ID[module_id]: "error"}


@pytest.mark.parametrize("module_id", CLASSIFIERS)
def test_retrain_text_names_all_materials_and_explains_why(module_id):
    module = _module(["metal", "other"], module_id, q5_other_material="carbon fiber")

    text = module["impacts"][0]["what_changes"]

    assert "metal" in text
    assert "carbon fiber" in text
    assert "shapes" in text
    assert "MAGICIAN" in text


@pytest.mark.parametrize("module_id", CLASSIFIERS)
def test_no_materials_gives_no_material_impact(module_id):
    result = compute_impacts(QuestionnaireAnswers(q_pipeline="both"), module_answers={})

    assert RETRAIN_FLAG_ID[module_id] not in _flags(result["module_impacts"][module_id])


def test_other_modules_keep_reconfigure_impacts_for_materials():
    result = compute_impacts(
        QuestionnaireAnswers(q_pipeline="both", q5_materials=["metal"]), module_answers={}
    )["module_impacts"]

    for module_id in ("orienteering_solver", "localiser"):
        assert _action_types(result[module_id]) == ["reconfigure"]


def _use_case(materials) -> UseCase:
    now = datetime.now(timezone.utc).isoformat()
    uc = UseCase(id="test", name="Test", created_at=now, updated_at=now)
    uc.answers = _answers(materials)
    return uc


@pytest.mark.parametrize("module_id", CLASSIFIERS)
def test_material_makes_classifier_need_action(module_id):
    uc = _use_case(["metal"])

    apply_impacts_to_modules(uc, compute_impacts(uc.answers, module_answers={}))

    assert [i.action_type for i in uc.modules[module_id].impacts] == ["retrain"]
    assert uc.modules[module_id].status == "needs_action"
