"""Dependency arrows on the module dashboard: which edges are visible, and how the grid shows them."""

import pytest
from PySide6.QtWidgets import QApplication

import app.engine.module_dependencies as deps
from app.engine.module_dependencies import (
    Dependency, VisibleEdge, scope_for, validate_configuration,
    visible_dependency_edges, visible_group_edges,
)
from app.engine.module_registry import MODULE_GROUPS, MODULES
from app.models.use_case import ModuleState
from gui.components.module_grid import ModuleGrid


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _cot_scope(pipeline, sensors=None):
    return [n for n in scope_for(pipeline, sensors) if n in MODULES]


def _pairs(edges):
    return [(e.provider, e.consumer) for e in edges]


def test_every_module_belongs_to_exactly_one_group():
    grouped = [m for group in MODULE_GROUPS.values() for m in group["modules"]]

    assert sorted(grouped) == sorted(MODULES)


def test_edge_within_a_group_is_a_module_arrow():
    assert ("grabber", "vision_classifier") in _pairs(visible_dependency_edges(_cot_scope("inspection")))


def test_module_arrows_only_connect_modules_of_the_same_group():
    edges = visible_dependency_edges(_cot_scope("both", ["tactile"]))

    group_of = {m: g for g, info in MODULE_GROUPS.items() for m in info["modules"]}
    assert edges and all(group_of[e.provider] == group_of[e.consumer] for e in edges)


def test_tactile_edge_follows_the_additional_sensors_answer():
    without = _pairs(visible_dependency_edges(_cot_scope("both")))
    with_tactile = _pairs(visible_dependency_edges(_cot_scope("both", ["tactile"])))

    assert ("grabber", "tactile_sensor") not in without
    assert ("grabber", "tactile_sensor") in with_tactile


def test_out_of_scope_module_has_no_incoming_or_outgoing_edges():
    edges = visible_dependency_edges(["vision_classifier", "localiser"])

    assert all("grabber" not in (e.provider, e.consumer) for e in edges)


def test_non_cot_nodes_are_never_drawn():
    scope = _cot_scope("both") + ["estimation_algorithm", "dmp_motion_planner"]

    assert all(n in MODULES for e in visible_dependency_edges(scope) for n in (e.provider, e.consumer))
    assert all(
        g in MODULE_GROUPS for e in visible_group_edges(scope) for g in (e.provider_group, e.consumer_group)
    )


def test_edges_are_derived_from_the_dependency_register(monkeypatch):
    monkeypatch.setattr(deps, "DEPENDENCIES", [
        Dependency(
            id="grabber_to_localiser", provider="grabber", consumer="localiser",
            provider_output="pose", consumer_input="pose", external_input_allowed=False,
            evidence_status="proposed", validation_status="owner_confirmation_needed",
        ),
    ])

    assert _pairs(visible_dependency_edges(["grabber", "localiser"])) == [("grabber", "localiser")]


def test_dependencies_between_groups_collapse_into_group_arrows():
    edges = visible_group_edges(_cot_scope("both", ["tactile"]))

    assert sorted((e.provider_group, e.consumer_group) for e in edges) == [
        ("defect_detection", "task_planning"),
        ("task_planning", "motion_planning"),
    ]


def test_group_arrow_appears_once_even_with_several_underlying_dependencies():
    edges = visible_group_edges(_cot_scope("both", ["tactile"]))

    assert [(e.provider_group, e.consumer_group) for e in edges].count(("defect_detection", "task_planning")) == 1


def test_group_arrow_needs_connected_in_scope_modules_on_both_sides():
    edges = visible_group_edges(["grabber", "vision_classifier", "localiser", "motion_planning", "ergodic_control"])

    assert edges == []


def test_localiser_and_ergodic_control_have_no_module_arrows():
    edges = visible_dependency_edges(_cot_scope("both", ["tactile"]))

    assert all(not {"localiser", "ergodic_control"} & {e.provider, e.consumer} for e in edges)


def test_display_only_edges_do_not_change_the_configuration_validation():
    result = validate_configuration("both", ["tactile"])

    assert result.status == "valid"
    assert result.owner_confirmation_needed == []
    assert result.blocking == []
    display_only_ids = {d.id for d in deps.DEPENDENCIES if d.display_only}
    assert display_only_ids and not display_only_ids & set(result.satisfied)


def _state(mid, status):
    return ModuleState(module_id=mid, module_name=mid, description="d", status=status)


def _all_states(status="ok", **overrides):
    return {m: _state(m, overrides.get(m, status)) for m in MODULES}


def test_grid_draws_arrows_only_between_in_scope_modules(qapp):
    grid = ModuleGrid()

    grid.update_modules({
        "grabber": _state("grabber", "ok"),
        "vision_classifier": _state("vision_classifier", "ok"),
        "tactile_sensor": _state("tactile_sensor", "out_of_scope"),
    })

    assert grid.dependency_edges() == [VisibleEdge("grabber", "vision_classifier")]


def test_grid_draws_no_arrows_while_not_assessed(qapp):
    grid = ModuleGrid()

    grid.update_modules(_all_states("not_assessed"))

    assert grid.dependency_edges() == []
    assert grid.group_edges() == []


def test_grid_draws_group_arrows_between_group_frames(qapp):
    grid = ModuleGrid()

    grid.update_modules(_all_states(tactile_sensor="out_of_scope"))

    assert {(e.provider_group, e.consumer_group) for e in grid.group_edges()} == {
        ("defect_detection", "task_planning"), ("task_planning", "motion_planning"),
    }


def test_grid_places_each_tile_inside_the_frame_of_its_group(qapp):
    grid = ModuleGrid()

    for group_id, info in MODULE_GROUPS.items():
        frame = grid.group_frame(group_id)
        for module_id in info["modules"]:
            assert grid.tile(module_id).parent() is frame


def test_grid_lays_groups_out_left_to_right_in_flow_order(qapp):
    grid = ModuleGrid()
    grid.resize(1000, 600)
    grid.update_modules(_all_states())
    grid.show()
    qapp.processEvents()

    frames = [grid.group_frame(g) for g in MODULE_GROUPS]
    lefts = [f.mapTo(grid, f.rect().topLeft()).x() for f in frames]
    tops = {f.mapTo(grid, f.rect().topLeft()).y() for f in frames}
    assert lefts == sorted(lefts) and len(set(lefts)) == len(lefts)
    assert len(tops) == 1


def test_provider_tile_sits_left_of_its_consumers_within_a_group(qapp):
    grid = ModuleGrid()

    grabber_col = grid.tile_cell("grabber")[1]
    assert grid.tile_cell("tactile_sensor")[1] > grabber_col
    assert grid.tile_cell("vision_classifier")[1] > grabber_col


def test_out_of_scope_tile_keeps_its_place(qapp):
    grid = ModuleGrid()
    before = {m: grid.tile_cell(m) for m in MODULES}

    grid.update_modules(_all_states(grabber="out_of_scope", tactile_sensor="out_of_scope"))

    assert {m: grid.tile_cell(m) for m in MODULES} == before

