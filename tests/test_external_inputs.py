"""
Guards ConfigurationValidationPanel: the free-text external source name is rendered in a
rich-text label, so markup in it must be shown literally.
"""

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from app.engine.module_dependencies import validate_configuration
from app.models.use_case import ExternalSource
from gui.components.external_inputs import ConfigurationValidationPanel


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
