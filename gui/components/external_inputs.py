"""
External input widgets:
  ConfigurationValidationPanel — page-level validation badge + required external inputs overview.
  ExternalInputForm            — per-requirement form (source, contract) shown in the consumer's ModuleDetail.
"""

from __future__ import annotations

from html import escape
from typing import List

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QCheckBox,
)
from PySide6.QtCore import Qt, Signal

from app.engine.module_dependencies import ConfigurationValidation, ExternalInputRequirement

# status -> (label, background, text colour)
_VALIDATION_STYLE = {
    "valid":                      ("Valid", "#d1fae5", "#065f46"),
    "valid_with_external_inputs": ("Valid (external inputs)", "#dbeafe", "#1e40af"),
    "incomplete":                 ("Incomplete", "#fef3c7", "#92400e"),
    "invalid":                    ("Invalid", "#fee2e2", "#991b1b"),
}


def _clear(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            _clear(item.layout())


class ConfigurationValidationPanel(QFrame):
    configure_requested = Signal(str)   # consumer module_id
    specification_requested = Signal()  # partner should answer the pipeline selection first

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame#validationPanel { background: white; border: 1px solid #e5e7eb; border-radius: 6px; }"
        )
        self.setObjectName("validationPanel")
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(14, 8, 14, 8)
        self._root.setSpacing(6)

    def update_validation(self, validation: ConfigurationValidation) -> None:
        _clear(self._root)

        header = QHBoxLayout()
        title = QLabel("Configuration validation")
        title.setStyleSheet("font-weight: 600; font-size: 12px; color: #111827; border: none;")
        header.addWidget(title)
        if validation.status == "not_assessed":
            header.addStretch()
            self._root.addLayout(header)
            self._root.addLayout(self._build_not_assessed_row())
            return
        label, bg, fg = _VALIDATION_STYLE.get(validation.status, (validation.status, "#f3f4f6", "#374151"))
        badge = QLabel(label)
        badge.setStyleSheet(
            f"background: {bg}; color: {fg}; border-radius: 8px; padding: 1px 8px; "
            "font-size: 11px; font-weight: bold; border: none;"
        )
        header.addWidget(badge)
        header.addStretch()
        self._root.addLayout(header)

        if validation.external_inputs:
            warning = QLabel(
                "MAGICIAN Inspection is not in scope, so the module(s) below still need input "
                "from an external source. Name the source and agree how it provides the data."
            )
            warning.setWordWrap(True)
            warning.setStyleSheet("color: #6b7280; font-size: 11px; border: none;")
            self._root.addWidget(warning)
            for req in validation.external_inputs:
                self._root.addLayout(self._build_row(req))

        for dep_id in validation.owner_confirmation_needed:
            self._root.addWidget(self._note(f"Owner confirmation needed for dependency '{dep_id}'."))
        for dep_id in validation.blocking:
            self._root.addWidget(self._note(f"Required input '{dep_id}' has no provider and cannot come from outside."))

    @staticmethod
    def _note(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #92400e; font-size: 11px; border: none;")
        return lbl

    def _build_not_assessed_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        hint = QLabel("Not assessed yet. Choose a pipeline selection in Use Case Specification.")
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 11px; color: #6b7280; border: none;")
        row.addWidget(hint, stretch=1)
        btn = QPushButton("Go to Use Case Specification")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton { border: 1px solid #d1d5db; background: white; color: #162759; "
            "padding: 2px 10px; border-radius: 4px; font-size: 11px; }"
        )
        btn.clicked.connect(self.specification_requested)
        row.addWidget(btn)
        return row

    def _build_row(self, req: ExternalInputRequirement) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        # The label renders rich text and the source name is free input.
        source = escape(req.source_name)
        if req.complete:
            state = f"Source: {source} \u00b7 contract agreed"
            colour = "#065f46"
        elif req.source_name.strip():
            state = f"Source: {source} \u00b7 contract not agreed yet"
            colour = "#92400e"
        else:
            state = "Source not set"
            colour = "#92400e"
        text = QLabel(
            f"<b>{req.consumer_name}</b>: <i>{req.input_name}</i> "
            f"(normally from {req.provider_name}) \u2014 <span style='color:{colour}'>{state}</span>"
        )
        text.setTextFormat(Qt.TextFormat.RichText)
        text.setWordWrap(True)
        text.setStyleSheet("font-size: 11px; color: #374151; border: none;")
        row.addWidget(text, stretch=1)
        btn = QPushButton("Configure")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton { border: 1px solid #d1d5db; background: white; color: #162759; "
            "padding: 2px 10px; border-radius: 4px; font-size: 11px; }"
        )
        btn.clicked.connect(lambda _=False, mid=req.consumer: self.configure_requested.emit(mid))
        row.addWidget(btn)
        return row


class ExternalInputForm(QFrame):
    source_changed = Signal(str, dict)   # (dependency_id, ExternalSource fields)

    def __init__(self, req: ExternalInputRequirement, parent=None) -> None:
        super().__init__(parent)
        self._req = req
        self.setStyleSheet("QFrame { border: 1px solid #fcd34d; border-radius: 6px; background: #fffbeb; }")
        vbox = QVBoxLayout(self)
        vbox.setSpacing(6)

        title = QLabel(f"External input required: {req.input_name}")
        title.setStyleSheet("font-weight: 600; border: none;")
        vbox.addWidget(title)

        info = QLabel(
            f"Normally provided by {req.provider_name}, which is not in scope for this pipeline selection. "
            "Name the external system that supplies it and agree how it delivers the data."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #6b7280; font-size: 11px; border: none;")
        vbox.addWidget(info)

        vbox.addWidget(self._fields_label("Required fields", req.minimum_fields))
        vbox.addWidget(self._fields_label("Conditional fields", req.conditional_fields))
        if req.external_schema:
            schema = QLabel(f"Contract schema: {req.external_schema}")
            schema.setStyleSheet("color: #6b7280; font-size: 11px; border: none;")
            vbox.addWidget(schema)

        self._name_edit = QLineEdit(req.source_name)
        self._name_edit.setPlaceholderText("External source name (e.g. partner inspection system)")
        vbox.addWidget(self._name_edit)
        self._agreed_cb = QCheckBox("Interface contract agreed with this source")
        self._agreed_cb.setChecked(req.contract_agreed)
        self._agreed_cb.setStyleSheet("border: none;")
        vbox.addWidget(self._agreed_cb)
        self._schema_edit = QLineEdit(req.schema_reference)
        self._schema_edit.setPlaceholderText("Agreed schema / interface reference (optional)")
        vbox.addWidget(self._schema_edit)

        save = QPushButton("Save external source")
        save.setStyleSheet(
            "background: #162759; color: white; padding: 4px 14px; border-radius: 4px; "
            "font-weight: bold; border: none;"
        )
        save.clicked.connect(self._emit)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(save)
        vbox.addLayout(row)

        # The dialog is rebuilt after every save, so this line always shows what is stored.
        saved = QLabel(self._saved_text(req))
        saved.setTextFormat(Qt.TextFormat.PlainText)
        saved.setWordWrap(True)
        saved.setStyleSheet(
            f"font-size: 11px; color: {'#065f46' if req.complete else '#92400e'}; border: none;"
        )
        vbox.addWidget(saved)

    @staticmethod
    def _saved_text(req: ExternalInputRequirement) -> str:
        if not req.source_name.strip():
            return "Not saved yet"
        agreed = "contract agreed" if req.contract_agreed else "contract not agreed yet"
        return f"Saved \u2014 source: {req.source_name} \u00b7 {agreed}"

    @staticmethod
    def _fields_label(title: str, fields: List[str]) -> QLabel:
        lbl = QLabel(f"{title}: {', '.join(fields) if fields else '-'}")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 11px; color: #374151; border: none;")
        return lbl

    def _emit(self) -> None:
        self.source_changed.emit(self._req.dependency_id, {
            "source_name": self._name_edit.text().strip(),
            "contract_agreed": self._agreed_cb.isChecked(),
            "schema_reference": self._schema_edit.text().strip(),
        })
