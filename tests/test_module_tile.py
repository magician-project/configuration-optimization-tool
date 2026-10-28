"""Module tiles on the dashboard stay compact: status and action types, no impact details."""

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from app.engine.module_registry import MODULES
from app.models.use_case import ModuleImpact, ModuleState
from gui.components.module_grid import ModuleGrid


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _texts(widget) -> list:
    return [w.text() for w in widget.findChildren(QLabel)]


def _impact(characteristic: str, action_type: str) -> ModuleImpact:
    return ModuleImpact(
        characteristic=characteristic, affects="a", what_changes="w", action_type=action_type, reason="r",
    )


def _grid_with(state: ModuleState) -> ModuleGrid:
    grid = ModuleGrid()
    grid.update_modules({state.module_id: state})
    return grid


def test_tile_shows_status_word_and_action_types_but_not_impact_text(qapp):
    state = ModuleState(
        module_id="grabber", module_name="Grabber", description="Core sensor driver", status="needs_action",
        impacts=[_impact("Addition of an extra sensor modality", "reconfigure"), _impact("Other", "review")],
    )

    texts = _texts(_grid_with(state).tile("grabber"))

    assert "Action required" in texts
    assert {"RECONFIGURE", "REVIEW"} <= set(texts)
    assert not any("extra sensor modality" in t or "more" in t for t in texts)


def test_tile_does_not_show_the_module_description(qapp):
    state = ModuleState(module_id="grabber", module_name="Grabber", description="d")

    texts = _texts(_grid_with(state).tile("grabber"))

    assert MODULES["grabber"]["description"] not in texts
    assert not any(t.startswith("Core sensor driver") for t in texts)


def test_tile_status_is_readable_as_text_not_only_as_colour(qapp):
    for status, text in (("ok", "Ready to validate"), ("validated", "Validated"), ("out_of_scope", "Out of scope")):
        state = ModuleState(module_id="grabber", module_name="Grabber", description="d", status=status)

        assert text in _texts(_grid_with(state).tile("grabber"))
