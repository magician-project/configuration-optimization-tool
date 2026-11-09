"""
Guards ConfigurationValidationPanel: the free-text external source name is rendered in a
rich-text label, so markup in it must be shown literally.
"""

import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from app.engine.module_dependencies import validate_configuration
from app.models.use_case import ExternalSource
from gui.components.external_inputs import ConfigurationValidationPanel
from gui.components.question_help_dialog import QuestionHelpDialog


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_source_name_markup_is_escaped_in_overview(qapp):
    sources = {"estimation_to_orienteering_solver": ExternalSource(source_name="Partner <AOI>")}
    panel = ConfigurationValidationPanel()

    panel.update_validation(validate_configuration("grinding", external_sources=sources))

    texts = [lbl.text() for lbl in panel.findChildren(QLabel)]
    assert any("Partner &lt;AOI&gt;" in t for t in texts)
    assert not any("<AOI>" in t for t in texts)


def _form(source: ExternalSource, dependency_id="estimation_to_orienteering_solver", module_answers=None):
    from gui.components.external_inputs import ExternalInputForm

    validation = validate_configuration(
        "grinding", external_sources={dependency_id: source}, module_answers=module_answers
    )
    [req] = [r for r in validation.external_inputs if r.dependency_id == dependency_id]
    return ExternalInputForm(req)


def _label_texts(widget) -> list:
    return [lbl.text() for lbl in widget.findChildren(QLabel)]


def test_form_shows_the_defect_type_and_frame_as_minimum_fields(qapp):
    texts = _label_texts(_form(ExternalSource()))

    [required] = [t for t in texts if t.startswith("Required fields")]
    assert "defect.type" in required and "coordinate_frame.frame_id" in required
    [conditional] = [t for t in texts if t.startswith("Conditional fields")]
    assert "defect.type" not in conditional and "coordinate_frame.frame_id" not in conditional
    assert any("defect class" in t for t in texts)


def test_form_for_a_capability_says_no_in_scope_module_provides_it(qapp):
    texts = _label_texts(_form(ExternalSource(), "measured_wrench"))

    assert "External input required: measured wrench" in texts
    assert any("no in-scope module provides" in t for t in texts)
    assert any(t.startswith("Required fields: measured_wrench_topic") for t in texts)
    assert not any("Normally provided by" in t for t in texts)


def test_panel_lists_a_missing_wrench_source_and_its_blocker(qapp):
    panel = ConfigurationValidationPanel()

    panel.update_validation(validate_configuration("grinding"))

    texts = _label_texts(panel)
    assert any("Impedance Controller" in t and "measured wrench" in t and "Source not set" in t for t in texts)
    assert any("measured_wrench_topic" in t for t in texts)


def _tile_texts(grid, module_id) -> list:
    return [lbl.text() for lbl in grid.tile(module_id).findChildren(QLabel, "capability_status")]


def test_capability_status_is_shown_on_the_consumer_tile_and_never_as_an_arrow(qapp):
    from app.engine.module_registry import MODULES
    from app.models.use_case import ModuleState
    from gui.components.module_grid import ModuleGrid

    grid = ModuleGrid()
    states = {m: ModuleState(module_id=m, module_name=m, description="d", status="ok") for m in MODULES}
    validation = validate_configuration("grinding")
    edges_without = None

    grid.update_modules(states)
    edges_without = (grid.dependency_edges(), grid.group_edges())
    grid.update_modules(states, capabilities=validation.capabilities)

    assert _tile_texts(grid, "impedance_controller") == ["Measured wrench: external input required"]
    assert _tile_texts(grid, "dmp") == ["Target frame: fender (Localiser)"]
    assert _tile_texts(grid, "localiser") == []
    assert (grid.dependency_edges(), grid.group_edges()) == edges_without


def test_form_says_nothing_is_saved_yet_for_a_new_requirement(qapp):
    assert "Not saved yet" in _label_texts(_form(ExternalSource()))


def test_form_confirms_a_saved_source_with_agreed_contract(qapp):
    form = _form(ExternalSource(source_name="Partner AOI", contract_agreed=True))

    assert "Saved \u2014 source: Partner AOI \u00b7 contract agreed" in _label_texts(form)


def test_form_says_what_is_missing_when_the_contract_is_not_agreed(qapp):
    form = _form(ExternalSource(source_name="Partner AOI"))

    assert "Saved \u2014 source: Partner AOI \u00b7 contract not agreed yet" in _label_texts(form)


def test_not_assessed_panel_shows_a_hint_and_no_validity_badge(qapp):
    panel = ConfigurationValidationPanel()

    panel.update_validation(validate_configuration(None))

    texts = _label_texts(panel)
    assert any("Choose a pipeline selection" in t for t in texts)
    assert not any(t in ("Valid", "Incomplete", "Invalid") for t in texts)


def test_not_assessed_panel_button_requests_the_specification_tab(qapp):
    from PySide6.QtWidgets import QPushButton

    panel = ConfigurationValidationPanel()
    panel.update_validation(validate_configuration(None))
    requested = []
    panel.specification_requested.connect(lambda: requested.append(True))

    next(b for b in panel.findChildren(QPushButton) if b.text().startswith("Go to")).click()

    assert requested == [True]


def _open_help(panel):
    from PySide6.QtWidgets import QPushButton, QTextBrowser

    panel.findChild(QPushButton, "validation_help").click()
    dialog = panel.findChild(QuestionHelpDialog)
    return dialog, dialog.findChild(QTextBrowser).toPlainText()


@pytest.mark.parametrize("pipeline", [None, "both", "grinding"])
def test_panel_offers_help_in_every_state(qapp, pipeline):
    panel = ConfigurationValidationPanel()
    panel.update_validation(validate_configuration(pipeline))

    dialog, _ = _open_help(panel)

    assert dialog.windowTitle() == "Configuration validation"


def test_help_explains_every_status_and_what_is_not_checked(qapp):
    panel = ConfigurationValidationPanel()
    panel.update_validation(validate_configuration("both"))

    _, text = _open_help(panel)

    for status in ("Valid", "Valid (external inputs)", "Incomplete", "Invalid", "Not assessed"):
        assert status in text
    assert "arrows" in text.lower()


def test_help_button_is_an_info_icon(qapp):
    panel = ConfigurationValidationPanel()
    panel.update_validation(validate_configuration("both"))

    assert panel.findChild(QPushButton, "validation_help").text() == "i"


def test_help_button_survives_a_refresh(qapp):
    panel = ConfigurationValidationPanel()

    panel.update_validation(validate_configuration("both"))
    panel.update_validation(validate_configuration("grinding"))
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    assert len(panel.findChildren(QPushButton, "validation_help")) == 1
