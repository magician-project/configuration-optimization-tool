"""
QuestionnaireForm — data-driven form that renders all 10 questions from SCHEMA.

Emits `answers_changed(dict)` whenever any field changes.
"""

from __future__ import annotations

import copy
from typing import NamedTuple

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QLineEdit, QSpinBox, QDoubleSpinBox,
    QScrollArea, QFrame,
)
from PySide6.QtCore import Qt, Signal

from app.engine.collection import collection_options, driver_answers, driver_question, selected_options
from app.engine.schema import SCHEMA
from gui.components.info_button import make_info_button
from gui.components.question_help_dialog import QuestionHelpDialog


class _NoScrollComboBox(QComboBox):
    """QComboBox that never responds to scroll wheel — use click to open."""
    def wheelEvent(self, event) -> None:
        event.ignore()


class _NoScrollSpinBox(QSpinBox):
    """QSpinBox that never responds to scroll wheel."""
    def wheelEvent(self, event) -> None:
        event.ignore()


class _NoScrollDoubleSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox that never responds to scroll wheel."""
    def wheelEvent(self, event) -> None:
        event.ignore()


_SECTION_ACCENT = {
    "A": "#162759",  # navy
    "B": "#0369a1",  # blue
    "C": "#0f766e",  # teal
    "D": "#7c3aed",  # purple
    "E": "#b45309",  # amber
}


class _CollectionRows(NamedTuple):
    question: dict
    rows: dict          # option value -> row widget
    empty_hint: QLabel  # shown while no allowed driver option is selected


def _collection_key(qid: str, option: str, field_id: str) -> str:
    # "." because question, option and field ids themselves contain "_".
    return f"{qid}.{option}.{field_id}"


class QuestionnaireForm(QScrollArea):
    answers_changed = Signal(dict)
    # (module_id, readme_anchor) — a question's help panel asked to open module documentation
    help_link_requested = Signal(str, str)

    def __init__(self, parent=None, questions: list | None = None, general_answers: dict | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        # Allow injecting a custom question list (e.g. module-specific config)
        self._questions = questions if questions is not None else SCHEMA["questions"]
        self._driver_answers = driver_answers(self._questions, general_answers or {})

        self._answers: dict = {}
        self._widgets: dict = {}   # field_id -> widget
        self._conditional_widgets: list = []  # widgets with conditions
        self._dimension_fields: dict = {}  # qid -> subfield ids (incl. "unit") for dimensions-type questions
        self._collections: dict[str, _CollectionRows] = {}

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(container)
        self._layout.setSpacing(14)
        self._layout.setContentsMargins(2, 4, 8, 4)

        self._build_form()
        self._layout.addStretch()
        self.setWidget(container)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def load_answers(self, answers: dict) -> None:
        # Deep copy: collection answers are nested, and edits must not leak into the caller's saved dict.
        self._answers = copy.deepcopy(answers)
        self._apply_answers_to_widgets()
        self._update_conditional_visibility()

    def get_answers(self) -> dict:
        return copy.deepcopy(self._answers)

    def set_general_answers(self, general_answers: dict) -> None:
        """Re-read the collection drivers from the general questionnaire and show the matching rows."""
        self._driver_answers = driver_answers(self._questions, general_answers)
        self._update_collection_rows()

    # ------------------------------------------------------------------
    # Build form
    # ------------------------------------------------------------------

    def _build_form(self) -> None:
        # If using module-specific questions (no section grouping), render flat
        has_sections = any(q.get("section") for q in self._questions)
        if has_sections:
            sections: dict[str, list] = {}
            for q in self._questions:
                sections.setdefault(q["section"], []).append(q)

            for section_def in SCHEMA["sections"]:
                sid = section_def["id"]
                qs = sections.get(sid, [])
                if not qs:
                    continue
                card = self._build_section_card(sid, section_def["title"], qs)
                if section_def.get("condition"):
                    card.setProperty("question_condition", section_def["condition"])
                    self._conditional_widgets.append(card)
                self._layout.addWidget(card)
        else:
            # Flat rendering — all questions in one list, no section cards
            for q in self._questions:
                question_widget = self._build_question(q)
                if q.get("condition"):
                    question_widget.setProperty("question_condition", q["condition"])
                    question_widget.setProperty("question_id", q["id"])
                    question_widget.setVisible(False)
                    self._conditional_widgets.append(question_widget)
                self._layout.addWidget(question_widget)

    def _build_section_card(self, sid: str, title: str, questions: list) -> QWidget:
        """Custom card with a coloured left accent bar instead of a QGroupBox."""
        accent = _SECTION_ACCENT.get(sid, "#162759")

        outer = QFrame()
        outer.setStyleSheet(
            "QFrame {"
            "  background: white;"
            "  border: 1px solid #e5e7eb;"
            "  border-radius: 8px;"
            "}"
        )
        outer_hbox = QHBoxLayout(outer)
        outer_hbox.setContentsMargins(0, 0, 0, 0)
        outer_hbox.setSpacing(0)

        # Accent bar on left
        accent_bar = QFrame()
        accent_bar.setFixedWidth(4)
        accent_bar.setStyleSheet(
            f"background: {accent}; border-radius: 4px 0 0 4px;"
        )
        outer_hbox.addWidget(accent_bar)

        # Content
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(16, 12, 16, 14)
        vbox.setSpacing(14)

        # Section header
        header_lbl = QLabel(f"Section {sid}  ·  {title}")
        header_lbl.setStyleSheet(
            f"color: {accent}; font-weight: bold; font-size: 12px; letter-spacing: 0.3px;"
        )
        vbox.addWidget(header_lbl)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"color: {accent}20;")
        div.setFixedHeight(1)
        vbox.addWidget(div)

        for q in questions:
            question_widget = self._build_question(q)
            # Store condition info if present for later visibility management
            if q.get("condition"):
                question_widget.setProperty("question_condition", q["condition"])
                question_widget.setProperty("question_id", q["id"])
                # Start as invisible if it has a condition
                question_widget.setVisible(False)
                self._conditional_widgets.append(question_widget)
            vbox.addWidget(question_widget)

        outer_hbox.addWidget(content, stretch=1)
        return outer

    def _build_question(self, q: dict) -> QWidget:
        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        vbox = QVBoxLayout(wrapper)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(5)

        # Title + tooltip
        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        title_lbl = QLabel(q["title"])
        title_lbl.setStyleSheet("font-weight: 600; color: #1f2937; font-size: 12px;")
        title_row.addWidget(title_lbl)
        if q.get("help_text") or q.get("tooltip"):
            help_btn = make_info_button(f"help_{q['id']}", q.get("tooltip") or "Click for more information")
            help_btn.clicked.connect(lambda _=False, q=q: self._show_help(q))
            title_row.addWidget(help_btn)
        title_row.addStretch()
        vbox.addLayout(title_row)

        # Input widget
        input_widget, follow_up_widget = self._build_input(q)
        vbox.addWidget(input_widget)
        if follow_up_widget:
            follow_up_widget.setVisible(False)
            vbox.addWidget(follow_up_widget)

        return wrapper

    def _show_help(self, q: dict) -> None:
        # Every panel opens with the short tooltip summary; help_text adds the detail sections.
        dlg = QuestionHelpDialog(
            q["title"], q.get("tooltip") or q["title"], q.get("help_text"), q.get("help_link"), parent=self,
        )
        dlg.documentation_requested.connect(self.help_link_requested)
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dlg.open()

    def _build_input(self, q: dict) -> tuple[QWidget, QWidget | None]:
        qtype = q["type"]
        qid = q["id"]
        follow_up_widget = None

        if qtype == "select":
            w = _NoScrollComboBox()
            w.addItem("— select —", None)
            for opt in q.get("options", []):
                w.addItem(opt["label"], opt["value"])
            self._widgets[qid] = w

            if q.get("follow_up"):
                follow_up_widget = self._build_follow_up(q["follow_up"])
                w.currentIndexChanged.connect(
                    lambda _, _w=w, _fu=follow_up_widget, _q=q:
                    self._on_select_changed(_w, _fu, _q)
                )
                # Also register for _update_conditional_visibility so reloaded
                # answers (set with blocked signals) still show this follow-up.
                follow_up_widget.setProperty("question_condition", q["follow_up"]["condition"])
                self._conditional_widgets.append(follow_up_widget)

            w.currentIndexChanged.connect(
                lambda _, _w=w, _id=qid: self._on_field_changed(_id, _w.currentData())
            )
            return w, follow_up_widget

        elif qtype == "checkbox":
            container = QWidget()
            container.setStyleSheet("background: transparent;")
            hbox = QHBoxLayout(container)
            hbox.setContentsMargins(0, 2, 0, 0)
            hbox.setSpacing(16)
            checkboxes: list[QCheckBox] = []
            for opt in q.get("options", []):
                cb = QCheckBox(opt["label"])
                cb.setProperty("cb_value", opt["value"])
                checkboxes.append(cb)
                hbox.addWidget(cb)
            hbox.addStretch()
            self._widgets[qid] = checkboxes

            if q.get("follow_up"):
                follow_up_widget = self._build_follow_up(q["follow_up"])
                for cb in checkboxes:
                    cb.stateChanged.connect(
                        lambda _, _cbs=checkboxes, _fu=follow_up_widget, _q=q:
                        self._on_checkbox_changed(_cbs, _fu, _q)
                    )
                # Also register for _update_conditional_visibility so reloaded
                # answers (set with blocked signals) still show this follow-up.
                follow_up_widget.setProperty("question_condition", q["follow_up"]["condition"])
                self._conditional_widgets.append(follow_up_widget)

            for cb in checkboxes:
                cb.stateChanged.connect(
                    lambda _, _cbs=checkboxes, _id=qid: self._on_field_changed(
                        _id, [c.property("cb_value") for c in _cbs if c.isChecked()]
                    )
                )
            return container, follow_up_widget

        elif qtype == "text":
            w = QLineEdit()
            w.setPlaceholderText(q.get("placeholder", ""))
            self._widgets[qid] = w
            w.textChanged.connect(lambda v, _id=qid: self._on_field_changed(_id, v or None))
            return w, follow_up_widget

        elif qtype == "number":
            w = _NoScrollSpinBox()
            w.setMinimum(q.get("min", 0))
            w.setMaximum(q.get("max", 9999))
            w.setValue(q.get("default", 0))
            self._widgets[qid] = w
            w.valueChanged.connect(lambda v, _id=qid: self._on_field_changed(_id, v))
            return w, follow_up_widget

        elif qtype == "number_float":
            w = _NoScrollDoubleSpinBox()
            # Decimals/step must be set before min/max/value: QDoubleSpinBox
            # rounds setMinimum()/setMaximum() to its *current* precision, so
            # setting them first would silently clamp e.g. min=0.0001 to 0.00.
            w.setDecimals(q.get("decimals", 2))
            w.setSingleStep(q.get("step", 0.01))
            w.setMinimum(q.get("min", 0.0))
            w.setMaximum(q.get("max", 9999.0))
            w.setValue(float(q.get("default", 0.0)))
            self._widgets[qid] = w
            w.valueChanged.connect(lambda v, _id=qid: self._on_field_changed(_id, v))
            return w, follow_up_widget

        elif qtype == "number_with_unit":
            container = QWidget()
            container.setStyleSheet("background: transparent;")
            hbox = QHBoxLayout(container)
            hbox.setContentsMargins(0, 0, 0, 0)
            hbox.setSpacing(8)

            spin = _NoScrollDoubleSpinBox()
            spin.setMinimum(q.get("min", 0.0))
            spin.setMaximum(9999.0)
            spin.setValue(float(q.get("default", 0.0)))
            spin.setFixedWidth(100)
            self._widgets[qid] = spin
            spin.valueChanged.connect(lambda v, _id=qid: self._on_field_changed(_id, v))

            unit_field = q.get("unit_field", qid + "_unit")
            unit_combo = _NoScrollComboBox()
            unit_combo.setFixedWidth(100)
            for u in q.get("units", ["minutes"]):
                unit_combo.addItem(u, u)
            default_unit = q.get("default_unit", "minutes")
            idx = unit_combo.findData(default_unit)
            if idx >= 0:
                unit_combo.setCurrentIndex(idx)
            self._widgets[unit_field] = unit_combo
            unit_combo.currentIndexChanged.connect(
                lambda _, _uc=unit_combo, _uid=unit_field: self._on_field_changed(_uid, _uc.currentData())
            )

            hbox.addWidget(spin)
            hbox.addWidget(unit_combo)
            hbox.addStretch()
            container.setLayout(hbox)
            return container, follow_up_widget

        elif qtype == "dimensions":
            container = QWidget()
            container.setStyleSheet("background: transparent;")
            hbox = QHBoxLayout(container)
            hbox.setContentsMargins(0, 0, 0, 0)
            hbox.setSpacing(8)

            dims_dict = {}
            for field in q.get("fields", []):
                hbox.addWidget(QLabel(field["label"] + ":"))
                spin = _NoScrollDoubleSpinBox()
                spin.setMinimum(0.0)
                spin.setMaximum(9999.0)
                spin.setDecimals(2)
                spin.setFixedWidth(110)
                field_key = f"{qid}_{field['id']}"
                dims_dict[field['id']] = spin
                self._widgets[field_key] = spin
                spin.valueChanged.connect(
                    lambda v, _fid=field["id"], _qid=qid: self._on_dimension_changed(_qid, _fid, v)
                )
                hbox.addWidget(spin)

            unit_cb = _NoScrollComboBox()
            unit_cb.setFixedWidth(80)
            for u in q.get("units", ["m"]):
                unit_cb.addItem(u, u)
            unit_key = f"{qid}_unit"
            self._widgets[unit_key] = unit_cb
            unit_cb.currentIndexChanged.connect(
                lambda _, _uc=unit_cb, _qid=qid: self._on_dimension_changed(_qid, "unit", _uc.currentData())
            )
            hbox.addWidget(unit_cb)
            hbox.addStretch()
            container.setLayout(hbox)
            self._dimension_fields[qid] = [f["id"] for f in q.get("fields", [])] + ["unit"]
            return container, follow_up_widget

        elif qtype == "collection":
            return self._build_collection(q), follow_up_widget

        return QWidget(), None

    def _build_collection(self, q: dict) -> QWidget:
        """One row of item fields per allowed driver option; only selected options' rows are shown."""
        qid = q["id"]
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(6)

        driver_title = driver_question(q)["title"]
        hint = QLabel(f"Nothing to configure yet: select an option in \u201c{driver_title}\u201d in the questionnaire.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #6b7280; font-size: 11px; font-style: italic;")
        vbox.addWidget(hint)

        rows: dict = {}
        for option in collection_options(q):
            row = QFrame()
            row.setStyleSheet(
                "QFrame {"
                "  background: #f8fafc;"
                "  border-left: 3px solid #c7d2fe;"
                "  border-radius: 0 6px 6px 0;"
                "}"
            )
            row_box = QVBoxLayout(row)
            row_box.setContentsMargins(12, 8, 12, 8)
            row_box.setSpacing(5)
            header = QLabel(option["label"])
            header.setStyleSheet("color: #1f2937; font-size: 11px; font-weight: 600; background: transparent;")
            row_box.addWidget(header)

            for field in q.get("item_fields", []):
                if field.get("type", "text") != "text":
                    raise ValueError(f"{qid}: unsupported collection item field type {field['type']!r}")
                lbl = QLabel(field.get("label", field["id"]))
                lbl.setStyleSheet("color: #374151; font-size: 11px; background: transparent;")
                row_box.addWidget(lbl)
                w = QLineEdit()
                w.setPlaceholderText(field.get("placeholder", ""))
                self._widgets[_collection_key(qid, option["value"], field["id"])] = w
                w.textChanged.connect(
                    lambda v, _opt=option["value"], _fid=field["id"]:
                    self._on_collection_changed(qid, _opt, _fid, v)
                )
                row_box.addWidget(w)

            rows[option["value"]] = row
            vbox.addWidget(row)

        self._collections[qid] = _CollectionRows(q, rows, hint)
        self._update_collection_rows()
        return container

    def _build_follow_up(self, follow_up: dict) -> QWidget:
        fq = follow_up["question"]
        fid = fq["id"]

        frame = QFrame()
        frame.setStyleSheet(
            "QFrame {"
            "  background: #f8fafc;"
            "  border-left: 3px solid #c7d2fe;"
            "  border-radius: 0 6px 6px 0;"
            "  margin-left: 6px;"
            "}"
        )
        vbox = QVBoxLayout(frame)
        vbox.setContentsMargins(12, 8, 12, 8)
        vbox.setSpacing(5)

        lbl = QLabel(fq.get("label", fid))
        lbl.setStyleSheet("color: #374151; font-size: 11px; font-weight: 600; background: transparent;")
        vbox.addWidget(lbl)

        ftype = fq.get("type")

        if ftype == "text":
            w = QLineEdit()
            w.setPlaceholderText(fq.get("placeholder", ""))
            self._widgets[fid] = w
            w.textChanged.connect(lambda v, _id=fid: self._on_field_changed(_id, v or None))
            vbox.addWidget(w)

        elif ftype == "number":
            w = _NoScrollSpinBox()
            w.setMinimum(fq.get("min", 0))
            w.setMaximum(fq.get("max", 9999))
            w.setValue(fq.get("default", 0))
            w.setFixedWidth(100)
            self._widgets[fid] = w
            w.valueChanged.connect(lambda v, _id=fid: self._on_field_changed(_id, v))
            vbox.addWidget(w)

        elif ftype == "number_with_unit":
            row = QHBoxLayout()
            row.setSpacing(8)
            spin = _NoScrollDoubleSpinBox()
            spin.setMinimum(fq.get("min", 0.0))
            spin.setMaximum(9999.0)
            spin.setValue(float(fq.get("default", 0.0)))
            spin.setFixedWidth(100)
            self._widgets[fid] = spin

            unit_field = fq.get("unit_field", fid + "_unit")
            unit_combo = _NoScrollComboBox()
            unit_combo.setFixedWidth(100)
            for u in fq.get("units", ["minutes"]):
                unit_combo.addItem(u, u)
            default_unit = fq.get("default_unit", "minutes")
            idx = unit_combo.findData(default_unit)
            if idx >= 0:
                unit_combo.setCurrentIndex(idx)
            self._widgets[unit_field] = unit_combo

            spin.valueChanged.connect(lambda v, _id=fid: self._on_field_changed(_id, v))
            unit_combo.currentIndexChanged.connect(
                lambda _, _uc=unit_combo, _uid=unit_field: self._on_field_changed(_uid, _uc.currentData())
            )
            row.addWidget(spin)
            row.addWidget(unit_combo)
            row.addStretch()
            vbox.addLayout(row)

        elif ftype == "select":
            w = _NoScrollComboBox()
            w.addItem("— select —", None)
            for opt in fq.get("options", []):
                w.addItem(opt["label"], opt["value"])
            self._widgets[fid] = w
            w.currentIndexChanged.connect(
                lambda _, _w=w, _id=fid: self._on_field_changed(_id, _w.currentData())
            )
            vbox.addWidget(w)

        elif ftype == "dimensions":
            grid = QHBoxLayout()
            grid.setSpacing(8)
            for field in fq.get("fields", []):
                grid.addWidget(QLabel(field["label"] + ":"))
                spin = _NoScrollDoubleSpinBox()
                spin.setMinimum(0.0)
                spin.setMaximum(9999.0)
                spin.setDecimals(2)
                spin.setFixedWidth(110)
                self._widgets[f"{fid}_{field['id']}"] = spin
                spin.valueChanged.connect(
                    lambda _, _spin=spin, _fid=field["id"], _qid=fid:
                    self._on_dimension_changed(_qid, _fid, _spin.value())
                )
                grid.addWidget(spin)
            unit_cb = QComboBox()
            unit_cb.setFixedWidth(80)
            for u in fq.get("units", ["m"]):
                unit_cb.addItem(u, u)
            self._widgets[f"{fid}_unit"] = unit_cb
            unit_cb.currentIndexChanged.connect(
                lambda _, _uc=unit_cb, _qid=fid: self._on_dimension_changed(_qid, "unit", _uc.currentData())
            )
            grid.addWidget(unit_cb)
            grid.addStretch()
            vbox.addLayout(grid)
            self._dimension_fields[fid] = [f["id"] for f in fq.get("fields", [])] + ["unit"]

        return frame

    # ------------------------------------------------------------------
    # Change handlers
    # ------------------------------------------------------------------

    def _on_field_changed(self, field_id: str, value) -> None:
        if value is None or value == [] or value == "":
            self._answers.pop(field_id, None)
        else:
            self._answers[field_id] = value
        self.answers_changed.emit(self._answers)

        # Update visibility of conditional questions
        self._update_conditional_visibility()

    def _update_conditional_visibility(self) -> None:
        """Show/hide conditional questions based on current answers."""
        for widget in self._conditional_widgets:
            cond = widget.property("question_condition")
            if not cond:
                continue

            field = cond.get("field")
            current_value = self._answers.get(field)
            visible = self._condition_met(cond, current_value)
            widget.setVisible(visible)

    def _on_dimension_changed(self, qid: str, subfield: str, value) -> None:
        dims = self._answers.get(qid, {})
        if not isinstance(dims, dict):
            dims = {}
        dims[subfield] = value
        self._answers[qid] = dims
        self.answers_changed.emit(self._answers)

    def _on_collection_changed(self, qid: str, option: str, field_id: str, value: str) -> None:
        # Empty levels are pruned so a cleared row leaves no trace in the saved answers.
        items = self._answers.get(qid)
        if not isinstance(items, dict):
            items = self._answers[qid] = {}
        item = items.get(option)
        if not isinstance(item, dict):
            item = items[option] = {}
        if value:
            item[field_id] = value
        else:
            item.pop(field_id, None)
            if not item:
                items.pop(option, None)
            if not items:
                self._answers.pop(qid, None)
        self.answers_changed.emit(self._answers)

    def _update_collection_rows(self) -> None:
        for collection in self._collections.values():
            selected = selected_options(collection.question, self._driver_answers)
            for option, row in collection.rows.items():
                row.setVisible(option in selected)
            collection.empty_hint.setVisible(not selected)

    def _on_select_changed(self, combo: QComboBox, follow_up_widget: QWidget, q: dict) -> None:
        value = combo.currentData()
        cond = q["follow_up"]["condition"]
        visible = self._condition_met(cond, value)
        follow_up_widget.setVisible(visible)

    def _on_checkbox_changed(self, checkboxes: list, follow_up_widget: QWidget, q: dict) -> None:
        selected = [cb.property("cb_value") for cb in checkboxes if cb.isChecked()]
        cond = q["follow_up"]["condition"]
        visible = self._condition_met(cond, selected)
        follow_up_widget.setVisible(visible)

    @staticmethod
    def _condition_met(cond: dict, value) -> bool:
        operator = cond.get("operator", "eq")
        if operator == "eq" or "operator" not in cond:
            return value == cond.get("value")
        elif operator == "in":
            return value in cond.get("values", [])
        elif operator == "not_in":
            return value not in cond.get("values", [])
        elif operator == "contains":
            return isinstance(value, list) and cond.get("value") in value
        return False

    # ------------------------------------------------------------------
    # Load answers into widgets
    # ------------------------------------------------------------------

    def _apply_answers_to_widgets(self) -> None:
        for field_id, widget in self._widgets.items():
            value = self._answers.get(field_id)
            if value is None:
                continue

            if isinstance(widget, list):
                for cb in widget:
                    cb.blockSignals(True)
                    cb.setChecked(cb.property("cb_value") in (value if isinstance(value, list) else []))
                    cb.blockSignals(False)
            elif isinstance(widget, QComboBox):
                idx = widget.findData(value)
                if idx >= 0:
                    widget.blockSignals(True)
                    widget.setCurrentIndex(idx)
                    widget.blockSignals(False)
            elif isinstance(widget, QSpinBox):
                widget.blockSignals(True)
                widget.setValue(int(value))
                widget.blockSignals(False)
            elif isinstance(widget, QDoubleSpinBox):
                widget.blockSignals(True)
                widget.setValue(float(value))
                widget.blockSignals(False)
            elif isinstance(widget, QLineEdit):
                widget.blockSignals(True)
                widget.setText(str(value))
                widget.blockSignals(False)

        # Dimensions-type questions store a dict answer (e.g. {"width": .., "height": ..}),
        # keyed separately from their per-subfield widgets, so they need their own pass.
        for qid, subfields in self._dimension_fields.items():
            dims = self._answers.get(qid)
            if not isinstance(dims, dict):
                continue
            for subfield in subfields:
                value = dims.get(subfield)
                if value is None:
                    continue
                widget = self._widgets.get(f"{qid}_{subfield}")
                if widget is None:
                    continue
                widget.blockSignals(True)
                if isinstance(widget, QComboBox):
                    idx = widget.findData(value)
                    if idx >= 0:
                        widget.setCurrentIndex(idx)
                elif isinstance(widget, QDoubleSpinBox):
                    widget.setValue(float(value))
                widget.blockSignals(False)

        for qid, collection in self._collections.items():
            items = self._answers.get(qid)
            items = items if isinstance(items, dict) else {}
            for option in collection.rows:
                item = items.get(option)
                item = item if isinstance(item, dict) else {}
                for field in collection.question.get("item_fields", []):
                    widget = self._widgets[_collection_key(qid, option, field["id"])]
                    widget.blockSignals(True)
                    widget.setText(str(item.get(field["id"]) or ""))
                    widget.blockSignals(False)
