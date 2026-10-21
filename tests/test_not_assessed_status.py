"""Module statuses on the dashboard and in the detail dialog: Not assessed, Ready to validate, Action required."""

import pytest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from app.models.use_case import ModuleState
from gui.components.module_detail import ModuleDetail
from gui.components.module_grid import ModuleGrid


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _state(status: str, module_id: str = "grabber") -> ModuleState:
    return ModuleState(module_id=module_id, module_name="Grabber", description="d", status=status)


def _texts(widget, kind=QLabel) -> list:
    return [w.text() for w in widget.findChildren(kind)]


def test_tile_labels_a_module_without_open_item_as_ready_to_validate(qapp):
    grid = ModuleGrid()

    grid.update_modules({"grabber": _state("ok")})

    assert "Ready to validate" in _texts(grid)
    assert "No action needed" not in _texts(grid)


def test_tile_labels_a_not_assessed_module(qapp):
    grid = ModuleGrid()

    grid.update_modules({"grabber": _state("not_assessed")})

    assert "Not assessed" in _texts(grid)


def test_summary_does_not_claim_everything_is_up_to_date_when_not_assessed(qapp):
    grid = ModuleGrid()

    grid.update_modules({mid: _state("not_assessed", mid) for mid in ("grabber", "localiser")})

    assert "All modules up to date" not in _texts(grid)


def test_ready_to_validate_module_offers_mark_as_validated(qapp):
    dlg = ModuleDetail(_state("ok"))

    assert "Mark as Validated" in _texts(dlg, QPushButton)
    assert "Status: Ready to validate" in _texts(dlg)


def test_not_assessed_module_offers_no_lifecycle_button(qapp):
    dlg = ModuleDetail(_state("not_assessed"))

    assert "Mark as Validated" not in _texts(dlg, QPushButton)
    assert any(t.startswith("Status: Not assessed") for t in _texts(dlg))
