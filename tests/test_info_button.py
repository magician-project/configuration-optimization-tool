"""The info button next to questions and the configuration validation: a neutral "i", not a blue "?"."""

import pytest
from PySide6.QtWidgets import QApplication, QPushButton

from gui.components.info_button import make_info_button
from gui.components.questionnaire_form import QuestionnaireForm

_BLUE_STYLE_VALUES = ("#e0e7ff", "#818cf8", "#c7d2fe", "#162759")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_info_button_is_a_named_i_with_a_tooltip(qapp):
    button = make_info_button("help_x", "Explains x")

    assert button.text() == "i"
    assert button.objectName() == "help_x"
    assert button.toolTip() == "Explains x"


def test_info_button_is_not_blue(qapp):
    style = make_info_button("help_x", "t").styleSheet().lower()

    assert not any(value in style for value in _BLUE_STYLE_VALUES)


def test_question_help_button_is_an_info_button(qapp):
    question = {
        "id": "q_test", "title": "Test", "type": "select", "options": [{"value": "a", "label": "A"}],
        "tooltip": "Short tip", "help_text": "Long text",
    }
    form = QuestionnaireForm(questions=[question])

    button = form.findChild(QPushButton, "help_q_test")

    assert button.text() == "i"
    assert button.toolTip() == "Short tip"
