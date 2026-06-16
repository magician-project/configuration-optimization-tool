"""
QuestionnaireForm — data-driven form that renders all 10 questions from SCHEMA.

Emits `answers_changed(dict)` whenever any field changes.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QLineEdit, QSpinBox, QDoubleSpinBox,
    QScrollArea, QFrame,
)
from PySide6.QtCore import Qt, Signal

from app.engine.schema import SCHEMA


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


class QuestionnaireForm(QScrollArea):
    answers_changed = Signal(dict)

    def __init__(self, parent=None, questions: list | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        # Allow injecting a custom question list (e.g. module-specific config)
        self._questions = questions if questions is not None else SCHEMA["questions"]

        self._answers: dict = {}
        self._widgets: dict = {}   # field_id -> widget
        self._conditional_widgets: list = []  # widgets with conditions

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
        self._answers = dict(answers)
        self._apply_answers_to_widgets()
        self._update_conditional_visibility()

    def get_answers(self) -> dict:
        return dict(self._answers)

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
                self._layout.addWidget(self._build_section_card(sid, section_def["title"], qs))
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
        if q.get("tooltip"):
            tip_lbl = QLabel("?")
            tip_lbl.setToolTip(q["tooltip"])
            tip_lbl.setFixedSize(16, 16)
            tip_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tip_lbl.setStyleSheet(
                "color: #6b7280; background: #f3f4f6; border: 1px solid #d1d5db; "
                "border-radius: 8px; font-size: 10px; font-weight: bold;"
            )
            title_row.addWidget(tip_lbl)
        title_row.addStretch()
        vbox.addLayout(title_row)

        # Input widget
        input_widget, follow_up_widget = self._build_input(q)
        vbox.addWidget(input_widget)
        if follow_up_widget:
            follow_up_widget.setVisible(False)
            vbox.addWidget(follow_up_widget)

        return wrapper

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
                spin.setFixedWidth(80)
                field_key = f"{qid}_{field['id']}"
                dims_dict[field['id']] = spin
                self._widgets[field_key] = spin
                spin.valueChanged.connect(
                    lambda v, _fid=field["id"], _qid=qid: self._on_dimension_changed(_qid, _fid, v)
                )
                hbox.addWidget(spin)

            unit_cb = _NoScrollComboBox()
            unit_cb.setFixedWidth(70)
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
            return container, follow_up_widget

        return QWidget(), None

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
                spin.setFixedWidth(80)
                self._widgets[f"q6_dimensions_{field['id']}"] = spin
                spin.valueChanged.connect(
                    lambda _, _spin=spin, _fid=field["id"]: self._on_dimension_changed(_fid, _spin.value())
                )
                grid.addWidget(spin)
            unit_cb = QComboBox()
            unit_cb.setFixedWidth(70)
            for u in fq.get("units", ["m"]):
                unit_cb.addItem(u, u)
            self._widgets["q6_dimensions_unit"] = unit_cb
            unit_cb.currentIndexChanged.connect(
                lambda _, _uc=unit_cb: self._on_dimension_changed("unit", _uc.currentData())
            )
            grid.addWidget(unit_cb)
            grid.addStretch()
            vbox.addLayout(grid)

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

    def _on_dimension_changed(self, subfield: str, value) -> None:
        dims = self._answers.get("q6_dimensions", {})
        if not isinstance(dims, dict):
            dims = {}
        dims[subfield] = value
        self._answers["q6_dimensions"] = dims
        self.answers_changed.emit(self._answers)

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
