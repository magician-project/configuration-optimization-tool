"""ModuleDetail: every module dialog offers a Documentation tab showing its README."""

import pytest
from PySide6.QtWidgets import QApplication, QTabWidget, QTextBrowser

from app.engine.module_registry import MODULES, README_EMPTY_STATE, module_readme_path
from app.models.use_case import ModuleState
from gui.components.module_detail import ModuleDetail

_CONFIGURABLE = {"vision_classifier", "ergodic_control", "grabber", "localiser", "motion_planning"}


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _dialog(module_id: str, status: str = "ok") -> ModuleDetail:
    info = MODULES[module_id]
    state = ModuleState(
        module_id=module_id, module_name=info["name"], description=info["description"], status=status,
    )
    return ModuleDetail(state)


def _tab_titles(dlg: ModuleDetail) -> list:
    tabs = dlg.findChild(QTabWidget)
    return [tabs.tabText(i) for i in range(tabs.count())]


@pytest.mark.parametrize("module_id", sorted(MODULES))
def test_every_module_has_a_documentation_tab_showing_its_readme(qapp, module_id):
    dlg = _dialog(module_id)

    assert "Documentation" in _tab_titles(dlg)
    shown = dlg.findChild(QTextBrowser).toPlainText()
    heading = module_readme_path(module_id).read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
    assert heading in shown
    assert README_EMPTY_STATE not in shown


@pytest.mark.parametrize("module_id", sorted(MODULES))
def test_documentation_is_available_for_out_of_scope_modules(qapp, module_id):
    dlg = _dialog(module_id, status="out_of_scope")

    assert "Documentation" in _tab_titles(dlg)


@pytest.mark.parametrize("module_id", sorted(MODULES))
def test_configuration_tab_only_for_modules_with_config_schema(qapp, module_id):
    titles = _tab_titles(_dialog(module_id))

    assert ("Module Configuration" in titles) == (module_id in _CONFIGURABLE)


def test_documentation_tab_survives_refresh(qapp):
    dlg = _dialog("orienteering_solver")
    info = MODULES["orienteering_solver"]

    dlg.refresh(ModuleState(
        module_id="orienteering_solver", module_name=info["name"],
        description=info["description"], status="validated",
    ))

    assert "Documentation" in _tab_titles(dlg)
