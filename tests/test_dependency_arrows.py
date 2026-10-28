"""Dependency arrows on the module dashboard: which edges are visible, and how the grid shows them."""

import pytest
from PySide6.QtWidgets import QApplication

import app.engine.module_dependencies as deps
from app.engine.module_dependencies import Dependency, scope_for, visible_dependency_edges
from app.models.use_case import ModuleState
from gui.components.module_grid import ModuleGrid


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _cot_scope(pipeline, sensors=None):
    return [n for n in scope_for(pipeline, sensors) if n in deps.MODULES]


def test_edge_between_two_in_scope_cot_modules_is_visible():
    assert ("grabber", "vision_classifier") in visible_dependency_edges(_cot_scope("inspection"))


def test_tactile_edge_follows_the_additional_sensors_answer():
    without = visible_dependency_edges(_cot_scope("both"))
    with_tactile = visible_dependency_edges(_cot_scope("both", ["tactile"]))

    assert ("grabber", "tactile_sensor") not in without
    assert ("grabber", "tactile_sensor") in with_tactile


def test_out_of_scope_module_has_no_incoming_or_outgoing_edges():
    edges = visible_dependency_edges(["vision_classifier", "localiser"])

    assert all("grabber" not in edge for edge in edges)


def test_non_cot_nodes_are_never_drawn():
    edges = visible_dependency_edges(_cot_scope("both") + ["estimation_algorithm", "dmp_motion_planner"])

    assert all(node in deps.MODULES for edge in edges for node in edge)


def test_edges_are_derived_from_the_dependency_register(monkeypatch):
    monkeypatch.setattr(deps, "DEPENDENCIES", [
        Dependency(
            id="localiser_to_vision", provider="localiser", consumer="vision_classifier",
            provider_output="pose", consumer_input="pose", external_input_allowed=False,
            evidence_status="proposed", validation_status="owner_confirmation_needed",
        ),
    ])

    assert visible_dependency_edges(["localiser", "vision_classifier"]) == [("localiser", "vision_classifier")]


def _state(mid, status):
    return ModuleState(module_id=mid, module_name=mid, description="d", status=status)


def test_grid_draws_arrows_only_between_in_scope_modules(qapp):
    grid = ModuleGrid()

    grid.update_modules({
        "grabber": _state("grabber", "ok"),
        "vision_classifier": _state("vision_classifier", "ok"),
        "tactile_sensor": _state("tactile_sensor", "out_of_scope"),
    })

    assert grid.dependency_edges() == [("grabber", "vision_classifier")]


def test_grid_draws_no_arrows_while_not_assessed(qapp):
    grid = ModuleGrid()

    grid.update_modules({m: _state(m, "not_assessed") for m in ("grabber", "vision_classifier")})

    assert grid.dependency_edges() == []
