"""A `verify` impact gets its own badge colour on the module tile and in the module detail dialog."""

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from app.models.use_case import ModuleImpact, ModuleState
from gui.components.module_detail import ModuleDetail
from gui.components.module_grid import ModuleGrid

_ACTION_TYPES = ["retrain", "reconfigure", "review", "verify"]
_FALLBACK = "#374151"


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _state(action_type: str) -> ModuleState:
    return ModuleState(
        module_id="vision_classifier", module_name="Vision Classifier", description="d",
        status="needs_action",
        impacts=[ModuleImpact(
            characteristic="c", affects="a", what_changes="w", action_type=action_type, reason="r",
        )],
    )


def _badge_style(widget, action_type: str) -> str:
    badge = next(lbl for lbl in widget.findChildren(QLabel) if lbl.text() == action_type.upper())
    return badge.styleSheet()


def _detail_badge_style(action_type: str) -> str:
    return _badge_style(ModuleDetail(_state(action_type)), action_type)


def _tile_badge_style(action_type: str) -> str:
    grid = ModuleGrid()
    grid.update_modules({"vision_classifier": _state(action_type)})
    return _badge_style(grid, action_type)


@pytest.mark.parametrize("badge_style", [_detail_badge_style, _tile_badge_style])
def test_verify_badge_has_its_own_colour(qapp, badge_style):
    verify = badge_style("verify")
    others = [badge_style(t) for t in _ACTION_TYPES if t != "verify"]

    assert _FALLBACK not in verify
    assert verify not in others
