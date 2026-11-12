"""
Impact rules of the IIT grinding modules (ticket 14): defect classes -> DMP, material -> Impedance
Controller, time constraint -> DMP and Cartesian Controller. The rules only detect and explain;
they never change a parameter.
"""

import pytest

from app.engine.grinding_cycle import BASELINE_PRIMITIVE_DURATION_S, baseline_cycle_time_s
from app.engine.questionnaire_engine import compute_impacts
from app.models.questionnaire import QuestionnaireAnswers

MATERIAL_FLAG = "flag_grinding_material"
FEASIBILITY_FLAG = "flag_grinding_cycle_infeasible"
CYCLE_MODULES = ("dmp", "cartesian_controller")
DEFAULT_CYCLE_S = 10.0 + 3.0 + 17.818 + 2.0 + 5.0


def _impacts(module_id, module_answers=None, **answers) -> dict:
    answers.setdefault("q_pipeline", "grinding")
    parsed = QuestionnaireAnswers(**answers)
    return compute_impacts(parsed, module_answers=module_answers or {})["module_impacts"][module_id]


def _flag_ids(module: dict) -> list:
    return [f["id"] for f in module["flags"]]


def _characteristic(module: dict, text: str):
    return next((i for i in module["impacts"] if text in i["characteristic"]), None)


def test_default_cycle_time_uses_the_larger_baseline_duration():
    assert baseline_cycle_time_s(["positive_dent", "negative_dent"], {}) == pytest.approx(DEFAULT_CYCLE_S)
    assert baseline_cycle_time_s(["positive_dent"], {}) == pytest.approx(DEFAULT_CYCLE_S - 17.818 + 17.717)


def test_cycle_time_follows_the_cartesian_controller_answers():
    cycle = baseline_cycle_time_s(["negative_dent"], {"reach_duration_s": 20.0, "go_away_duration_s": 0.0})
    assert cycle == pytest.approx(20.0 + 3.0 + 17.818 + 2.0 + 0.0)


@pytest.mark.parametrize("classes", [[], ["other"]])
def test_no_cycle_time_without_a_class_that_has_a_baseline(classes):
    assert baseline_cycle_time_s(classes, {}) is None


def test_baseline_durations_are_the_iit_values():
    assert BASELINE_PRIMITIVE_DURATION_S == {"negative_dent": 17.818, "positive_dent": 17.717}


# --- Q8 -> DMP -------------------------------------------------------------

def test_defect_classes_give_the_dmp_a_primitive_impact():
    dmp = _impacts("dmp", q8_defects=["positive_dent", "negative_dent"])
    impact = _characteristic(dmp, "Defect classes")
    assert "configure learned grinding primitive for: Positive Dent, Negative Dent" in impact["what_changes"]


def test_other_defect_class_is_listed_by_its_description():
    dmp = _impacts("dmp", q8_defects=["other"], q8_other_defect="scratch")
    impact = _characteristic(dmp, "Defect classes")
    assert "scratch" in impact["what_changes"]


def test_no_primitive_impact_without_defect_classes():
    assert _characteristic(_impacts("dmp"), "Defect classes") is None


def test_inspection_only_gives_the_dmp_nothing():
    dmp = _impacts("dmp", q_pipeline="inspection", q8_defects=["positive_dent"], q5_materials=["metal"],
                   q9_time="tight", q9_time_value=1, q9_time_unit="seconds")
    assert dmp == {"impacts": [], "flags": []}


# --- Q5 -> Impedance Controller ----------------------------------------------

def test_material_flags_the_impedance_controller_for_review():
    module = _impacts("impedance_controller", q5_materials=["metal"])
    flag = next(f for f in module["flags"] if f["id"] == MATERIAL_FLAG)
    assert flag["type"] == "human_oversight"
    assert flag["message"] == (
        "Validated material/tool/contact-control configuration required. "
        "COT does not infer or tune controller gains from the selected material."
    )


def test_other_material_also_flags_the_impedance_controller():
    assert MATERIAL_FLAG in _flag_ids(_impacts("impedance_controller", q5_materials=["other"]))


def test_no_material_flag_without_a_material():
    assert MATERIAL_FLAG not in _flag_ids(_impacts("impedance_controller"))


def test_no_material_flag_for_inspection_only():
    module = _impacts("impedance_controller", q_pipeline="inspection", q5_materials=["metal"])
    assert module == {"impacts": [], "flags": []}


def test_material_does_not_flag_the_other_grinding_modules():
    for module_id in ("dmp", "cartesian_controller"):
        assert MATERIAL_FLAG not in _flag_ids(_impacts(module_id, q5_materials=["metal"]))


# --- Q9 -> DMP and Cartesian Controller -----------------------------------------

def _time(module_id, value, unit="seconds", classes=("positive_dent", "negative_dent"), module_answers=None):
    return _impacts(module_id, module_answers, q8_defects=list(classes),
                    q9_time="tight", q9_time_value=value, q9_time_unit=unit)


@pytest.mark.parametrize("module_id", CYCLE_MODULES)
def test_budget_shorter_than_one_cycle_gives_a_feasibility_flag(module_id):
    module = _time(module_id, 30)
    flag = next(f for f in module["flags"] if f["id"] == FEASIBILITY_FLAG)
    assert flag["type"] == "warning"
    assert "37.8 s" in flag["message"]
    assert "30" in flag["message"]
    assert "IIT baseline, not measured from configured primitive files" in flag["message"]
    assert _characteristic(module, "baseline cycles") is None


@pytest.mark.parametrize("module_id", CYCLE_MODULES)
def test_budget_of_five_minutes_reports_seven_baseline_cycles(module_id):
    module = _time(module_id, 5, unit="minutes")
    assert FEASIBILITY_FLAG not in _flag_ids(module)
    impact = _characteristic(module, "baseline cycles")
    assert impact["action_type"] == "review"
    assert "7 baseline cycles" in impact["what_changes"]
    assert "not a prediction" in impact["what_changes"]
    assert "IIT baseline, not measured from configured primitive files" in impact["what_changes"]


def test_budget_in_hours_is_converted():
    impact = _characteristic(_time("dmp", 1, unit="hours"), "baseline cycles")
    assert "95 baseline cycles" in impact["what_changes"]


def test_budget_exactly_one_cycle_fits():
    impact = _characteristic(_time("dmp", DEFAULT_CYCLE_S, classes=("negative_dent",)), "baseline cycles")
    assert "1 baseline cycle" in impact["what_changes"]


def test_cycle_time_uses_the_current_cartesian_answers():
    # Default cycle is 37.8 s (fits 40 s); a 60 s reach makes it 87.8 s.
    assert FEASIBILITY_FLAG not in _flag_ids(_time("dmp", 40))
    assert FEASIBILITY_FLAG in _flag_ids(_time("dmp", 40, module_answers={"cartesian_controller": {"reach_duration_s": 60.0}}))
    assert FEASIBILITY_FLAG not in _flag_ids(_time("dmp", 100, module_answers={"cartesian_controller": {"reach_duration_s": 60.0}}))


@pytest.mark.parametrize("answers", [
    {"q9_time": "none"},
    {"q9_time": "tight"},
    {"q9_time": "tight", "q9_time_value": 0},
    {},
])
def test_no_budget_gives_no_cycle_rule(answers):
    for module_id in CYCLE_MODULES:
        module = _impacts(module_id, q8_defects=["positive_dent"], **answers)
        assert FEASIBILITY_FLAG not in _flag_ids(module)
        assert _characteristic(module, "baseline cycles") is None


def test_no_cycle_rule_without_a_defect_class_with_a_baseline():
    module = _time("dmp", 30, classes=("other",))
    assert FEASIBILITY_FLAG not in _flag_ids(module)
    assert _characteristic(module, "baseline cycles") is None


def test_cycle_rule_is_not_applied_to_the_impedance_controller():
    module = _time("impedance_controller", 30)
    assert FEASIBILITY_FLAG not in _flag_ids(module)


def test_rules_never_change_a_parameter():
    answers = {"cartesian_controller": {"reach_duration_s": 60.0}}
    before = {"cartesian_controller": dict(answers["cartesian_controller"])}
    _time("cartesian_controller", 30, module_answers=answers)
    assert answers == before
