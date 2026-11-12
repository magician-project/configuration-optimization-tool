"""ModuleDetail: every module dialog offers a Documentation tab showing its README."""

import pytest
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QTabWidget, QTextBrowser

from app.engine.module_registry import MODULES, README_EMPTY_STATE, module_readme_path
from app.models.use_case import Flag, ModuleState
from gui.components.module_detail import ModuleDetail

_CONFIGURABLE = {
    "vision_classifier", "ergodic_control", "grabber", "localiser", "motion_planning", "dmp",
    "cartesian_controller", "impedance_controller",
}


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


def test_impacts_tab_title_shows_the_ampersand(qapp):
    # A single "&" is a Qt mnemonic marker and is not displayed; "&&" renders as "&".
    assert "Impacts && Flags" in _tab_titles(_dialog("grabber"))


def _dialog_with_flags(acknowledged: bool = False) -> ModuleDetail:
    info = MODULES["grabber"]
    flags = [Flag(id="f1", type="warning", message="Check the gripper", module_id="grabber",
                  acknowledged=acknowledged)]
    state = ModuleState(
        module_id="grabber", module_name=info["name"], description=info["description"],
        status="needs_action", flags=flags,
    )
    return ModuleDetail(state)


def _acknowledge_button(dlg: ModuleDetail):
    return next(b for b in dlg.findChildren(QPushButton) if "flag(s)" in b.text())


def test_flags_tab_title_counts_the_open_flags(qapp):
    assert _tab_titles(_dialog_with_flags())[1] == "Impacts && Flags (1)"
    assert _tab_titles(_dialog_with_flags(acknowledged=True))[1] == "Impacts && Flags"


def test_open_flags_must_be_reviewed_before_they_can_be_acknowledged(qapp):
    dlg = _dialog_with_flags()
    requested = []
    dlg.action_requested.connect(lambda module_id, action: requested.append(action))
    button = _acknowledge_button(dlg)
    assert button.text() == "Review 1 flag(s)"

    button.click()

    tabs = dlg.findChild(QTabWidget)
    assert tabs.tabText(tabs.currentIndex()) == "Impacts && Flags (1)"
    assert requested == []
    assert _acknowledge_button(dlg).text() == "Acknowledge 1 flag(s)"

    _acknowledge_button(dlg).click()

    assert requested == ["acknowledge"]


def test_configuration_tab_comes_before_the_flags_tab(qapp):
    dlg = _dialog("grabber")

    assert _tab_titles(dlg) == ["Module Configuration", "Impacts && Flags", "Documentation"]
    tabs = dlg.findChild(QTabWidget)
    assert tabs.tabText(tabs.currentIndex()) == "Module Configuration"


def test_module_without_configuration_opens_on_the_flags_tab(qapp):
    assert _tab_titles(_dialog("orienteering_solver")) == ["Impacts && Flags", "Documentation"]


def test_refresh_keeps_the_selected_tab(qapp):
    dlg = _dialog("grabber")
    tabs = dlg.findChild(QTabWidget)
    tabs.setCurrentIndex(1)

    dlg.refresh(dlg._module)

    tabs = dlg.findChild(QTabWidget)
    assert tabs.tabText(tabs.currentIndex()) == "Impacts && Flags"


def test_documentation_tab_survives_refresh(qapp):
    dlg = _dialog("orienteering_solver")
    info = MODULES["orienteering_solver"]

    dlg.refresh(ModuleState(
        module_id="orienteering_solver", module_name=info["name"],
        description=info["description"], status="validated",
    ))

    # refresh() only schedules deletion of the old tabs; process it so findChild sees the rebuilt ones.
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    assert "Documentation" in _tab_titles(dlg)
    banners = [lbl.text() for lbl in dlg.findChildren(QLabel) if lbl.text().startswith("Status:")]
    assert banners == ["Status: Validated — ready to compute"]


def _click_doc_link(dlg: ModuleDetail, markdown: str, href: str) -> None:
    """Show `markdown` in the Documentation tab and click the link whose target is `href`."""
    tabs = dlg.findChild(QTabWidget)
    tabs.setCurrentIndex(tabs.count() - 1)
    browser = dlg.findChild(QTextBrowser)
    browser.setMarkdown(markdown)
    dlg.resize(900, 700)
    dlg.show()
    QApplication.processEvents()
    viewport = browser.viewport()
    point = next(
        QPoint(x, y)
        for y in range(0, viewport.height(), 4)
        for x in range(0, viewport.width(), 4)
        if browser.anchorAt(QPoint(x, y)) == href
    )
    QTest.mouseClick(viewport, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)
    QApplication.processEvents()


@pytest.fixture
def opened_urls(monkeypatch):
    urls = []
    monkeypatch.setattr(QDesktopServices, "openUrl", staticmethod(lambda url: urls.append(url.toString()) or True))
    return urls


def test_clicking_an_external_link_opens_it_in_the_browser(qapp, opened_urls):
    _click_doc_link(_dialog("localiser"), "[docs](https://example.com/doc)", "https://example.com/doc")

    assert opened_urls == ["https://example.com/doc"]


def test_clicking_a_relative_link_opens_the_target_file(qapp, opened_urls):
    _click_doc_link(_dialog("localiser"), "[ctx](../../CONTEXT.md)", "../../CONTEXT.md")

    assert len(opened_urls) == 1
    assert opened_urls[0].startswith("file:///") and opened_urls[0].endswith("/CONTEXT.md")


def test_clicking_a_link_to_a_file_outside_the_repo_opens_nothing(qapp, opened_urls):
    _click_doc_link(_dialog("localiser"), "[x](file:///etc/passwd)", "file:///etc/passwd")

    assert opened_urls == []
