"""Clickable help (`?`) next to questionnaire questions."""

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QTabWidget, QTextBrowser

from app.engine.module_registry import heading_anchor, readme_anchors
from app.engine.schema import SCHEMA
from app.models.use_case import ModuleState
from gui.components.module_detail import ModuleDetail
from gui.components.question_help_dialog import QuestionHelpDialog
from gui.components.questionnaire_form import QuestionnaireForm


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _question(**extra) -> dict:
    return {
        "id": "q_test", "title": "Test question", "type": "select",
        "options": [{"value": "a", "label": "A"}],
        "tooltip": "Short summary.", **extra,
    }


def _help_button(form: QuestionnaireForm) -> QPushButton | None:
    return form.findChild(QPushButton, "help_q_test")


def test_heading_anchor_follows_github_slug_rules():
    assert heading_anchor("OP variant selection logic") == "op-variant-selection-logic"
    assert heading_anchor("External defect input (grinding only)") == "external-defect-input-grinding-only"
    assert heading_anchor("Module-specific hardware configuration (Grabber Config tab)") == (
        "module-specific-hardware-configuration-grabber-config-tab"
    )


def test_readme_anchors_ignore_headings_inside_code_fences():
    anchors = readme_anchors("vision_classifier")

    assert "how-to-implement-training" in anchors
    assert "train.py-skeleton" not in anchors and "trainpy-skeleton" not in anchors


def test_question_with_help_text_gets_a_clickable_help_button_that_keeps_its_tooltip(qapp):
    form = QuestionnaireForm(questions=[_question(help_text="Long explanation.")])

    button = _help_button(form)

    assert button is not None
    assert button.toolTip() == "Short summary."


def test_question_with_only_a_tooltip_also_gets_the_clickable_help_showing_the_tooltip_text(qapp):
    form = QuestionnaireForm(questions=[_question()])

    button = _help_button(form)
    assert button is not None
    button.click()

    dlg = form.findChild(QuestionHelpDialog)
    assert dlg.isVisible()
    assert dlg.findChild(QTextBrowser).toPlainText() == "Short summary."
    dlg.close()


def test_question_without_tooltip_or_help_text_has_no_help_button(qapp):
    question = _question()
    del question["tooltip"]

    assert _help_button(QuestionnaireForm(questions=[question])) is None


def test_every_question_with_a_tooltip_has_the_same_clickable_help(qapp):
    form = QuestionnaireForm()

    for q in SCHEMA["questions"]:
        if q.get("tooltip") or q.get("help_text"):
            assert form.findChild(QPushButton, f"help_{q['id']}") is not None, q["id"]
    assert not [lbl for lbl in form.findChildren(QLabel) if lbl.text() == "?"]


def test_clicking_help_opens_a_panel_with_the_explanation(qapp):
    form = QuestionnaireForm(questions=[_question(help_text="Long **explanation** here.")])

    _help_button(form).click()

    dlg = form.findChild(QuestionHelpDialog)
    assert dlg is not None and dlg.isVisible()
    assert "Long explanation here." in dlg.findChild(QTextBrowser).toPlainText()
    dlg.close()


def test_panel_opens_with_the_tooltip_summary_followed_by_the_detail_sections(qapp):
    form = QuestionnaireForm(questions=[_question(help_text="**Example**\n\nA *concrete* case.")])

    _help_button(form).click()

    dlg = form.findChild(QuestionHelpDialog)
    shown = dlg.findChild(QTextBrowser).toPlainText()
    assert shown.startswith("Short summary.")
    assert "Example" in shown and "A concrete case." in shown
    dlg.close()


def test_tooltip_summary_with_markdown_characters_is_shown_literally(qapp):
    form = QuestionnaireForm(questions=[_question(tooltip="Use my_topic_name and 1/3600 (*not* 2-3).")])

    _help_button(form).click()

    dlg = form.findChild(QuestionHelpDialog)
    assert dlg.findChild(QTextBrowser).toPlainText().strip() == "Use my_topic_name and 1/3600 (*not* 2-3)."
    dlg.close()


def test_panel_without_help_link_offers_no_documentation_button(qapp):
    form = QuestionnaireForm(questions=[_question(help_text="Long explanation.")])
    _help_button(form).click()

    dlg = form.findChild(QuestionHelpDialog)
    assert dlg.findChild(QPushButton, "open_documentation") is None
    dlg.close()


def test_help_link_requests_documentation_and_closes_the_panel(qapp):
    form = QuestionnaireForm(questions=[_question(
        help_text="Long explanation.", help_link={"module": "grabber", "anchor": "inputs-from-questionnaire"},
    )])
    requests = []
    form.help_link_requested.connect(lambda module, anchor: requests.append((module, anchor)))
    _help_button(form).click()
    dlg = form.findChild(QuestionHelpDialog)

    dlg.findChild(QPushButton, "open_documentation").click()

    assert requests == [("grabber", "inputs-from-questionnaire")]
    assert not dlg.isVisible()


def test_q10_profit_and_q_pipeline_show_their_full_help(qapp):
    questions = [q for q in SCHEMA["questions"] if q["id"] in {"q10_profit", "q_pipeline"}]
    form = QuestionnaireForm(questions=questions)

    for q in questions:
        button = form.findChild(QPushButton, f"help_{q['id']}")
        assert button is not None, q["id"]
        button.click()
        dlg = form.findChild(QuestionHelpDialog)
        assert dlg.isVisible()
        assert dlg.findChild(QTextBrowser).toPlainText().strip()
        dlg.close()
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def _blocks(browser: QTextBrowser):
    block = browser.document().begin()
    while block.isValid():
        yield block
        block = block.next()


def _module_dialog(module_id: str = "orienteering_solver") -> ModuleDetail:
    return ModuleDetail(ModuleState(module_id=module_id, module_name="Module", description="d", status="ok"))


def test_show_documentation_switches_to_the_documentation_tab_at_the_section(qapp):
    from PySide6.QtWidgets import QTabWidget

    dlg = _module_dialog()
    dlg.resize(900, 300)
    dlg.show()
    QApplication.processEvents()

    dlg.show_documentation("external-defect-input-grinding-only")
    QApplication.processEvents()

    tabs = dlg.findChild(QTabWidget)
    assert tabs.tabText(tabs.currentIndex()) == "Documentation"
    browser = dlg.findChild(QTextBrowser)
    heading = next(
        b for b in _blocks(browser) if b.text() == "External defect input (grinding only)"
    )
    heading_top = browser.document().documentLayout().blockBoundingRect(heading).top()
    assert browser.verticalScrollBar().value() == pytest.approx(heading_top, abs=40)
    dlg.close()


def test_show_documentation_with_unknown_anchor_still_opens_the_tab(qapp):
    from PySide6.QtWidgets import QTabWidget

    dlg = _module_dialog()

    dlg.show_documentation("no-such-section")

    tabs = dlg.findChild(QTabWidget)
    assert tabs.tabText(tabs.currentIndex()) == "Documentation"
