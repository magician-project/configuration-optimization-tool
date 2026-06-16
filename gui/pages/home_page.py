"""
HomePage — lists all use cases and allows creating a new one.
Emits open_use_case(use_case_id) when the user opens a use case.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QFrame, QMessageBox,
)
from PySide6.QtCore import Qt, Signal
from datetime import datetime, timezone


from app.engine.questionnaire_engine import apply_impacts_to_modules
from app.storage import json_store
from app.models import UseCase

import uuid


_CONF_STYLE = {
    "high":   "#16a34a",
    "medium": "#d97706",
    "low":    "#dc2626",
}


class HomePage(QWidget):
    open_use_case = Signal(str)   # use_case_id

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        self.setStyleSheet("background: #f0f2f5;")
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)

        # Hero
        hero_lbl = QLabel("Configuration Optimization Tool")
        hero_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #162759;")
        root.addWidget(hero_lbl)
        sub_lbl = QLabel(
            "Configure MAGICIAN modules for a new use case by answering the questionnaire. "
            "COT computes the required parameter changes and fires them to the ROS 2 framework."
        )
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet("color: #6b7280;")
        root.addWidget(sub_lbl)

        # Create new use case
        create_box = QFrame()
        create_box.setStyleSheet(
            "QFrame { border: 1px solid #e5e7eb; border-radius: 8px; background: white; }"
        )
        create_layout = QHBoxLayout(create_box)
        create_layout.setContentsMargins(14, 10, 14, 10)
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Enter use case name…")
        self._name_input.setMinimumWidth(280)
        self._name_input.setStyleSheet(
            "border: 1px solid #d1d5db; border-radius: 5px; padding: 6px 10px; font-size: 13px;"
        )
        self._name_input.returnPressed.connect(self._create_use_case)
        create_layout.addWidget(self._name_input)
        create_btn = QPushButton("+ Create use case")
        create_btn.setStyleSheet(
            "background: #162759; color: white; padding: 6px 20px; border-radius: 5px; "
            "font-weight: bold; font-size: 12px; border: none;"
        )
        create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_btn.clicked.connect(self._create_use_case)
        create_layout.addWidget(create_btn)
        create_layout.addStretch()
        root.addWidget(create_box)

        # Use case list
        list_lbl = QLabel("Use Cases")
        list_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #162759;")
        root.addWidget(list_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setSpacing(8)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.addStretch()
        scroll.setWidget(self._list_container)
        root.addWidget(scroll, stretch=1)

    def refresh(self) -> None:
        # Clear existing entries (keep stretch at end)
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        use_cases = json_store.list_all()
        if not use_cases:
            empty = QLabel("No use cases yet. Create one above.")
            empty.setStyleSheet("color: #9ca3af; padding: 12px;")
            self._list_layout.insertWidget(0, empty)
            return

        for uc in use_cases:
            card = self._build_use_case_card(uc)
            self._list_layout.insertWidget(self._list_layout.count() - 1, card)

    def _build_use_case_card(self, uc: UseCase) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { border: 1px solid #e5e7eb; border-radius: 8px; background: white; }"
        )
        hbox = QHBoxLayout(frame)
        hbox.setContentsMargins(14, 10, 10, 10)

        # Left: name + meta
        vbox = QVBoxLayout()
        name_btn = QPushButton(uc.name)
        name_btn.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #162759; "
            "border: none; text-align: left; padding: 0; background: transparent;"
        )
        name_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        name_btn.clicked.connect(lambda _, _id=uc.id: self.open_use_case.emit(_id))
        vbox.addWidget(name_btn)

        try:
            dt = datetime.fromisoformat(uc.updated_at)
            updated_str = dt.strftime("%d %b %Y %H:%M")
        except Exception:
            updated_str = uc.updated_at
        meta = QLabel(f"ID: {uc.id}  ·  Updated: {updated_str}")
        meta.setStyleSheet("color: #9ca3af; font-size: 11px;")
        vbox.addWidget(meta)

        # Module status counts
        needs = sum(1 for m in uc.modules.values() if m.status == "needs_action")
        deployed = sum(1 for m in uc.modules.values() if m.status == "deployed")
        status_parts = []
        if needs:
            status_parts.append(f"{needs} pending")
        elif uc.modules:
            status_parts.append("No pending")
        if deployed:
            status_parts.append(f"{deployed} deployed")
        if status_parts:
            status_lbl = QLabel("  ".join(status_parts))
            status_lbl.setStyleSheet("font-size: 11px; color: #374151;")
            vbox.addWidget(status_lbl)

        hbox.addLayout(vbox, stretch=1)

        # Confidence badge
        conf = uc.confidence
        col = _CONF_STYLE.get(conf.level, "#6b7280")
        conf_lbl = QLabel(f"{conf.score}/{conf.max}\n{conf.level.upper()}")
        conf_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        conf_lbl.setStyleSheet(
            f"color: {col}; font-weight: bold; font-size: 11px; min-width: 48px;"
        )
        hbox.addWidget(conf_lbl)

        # Delete button
        del_btn = QPushButton("✕")
        del_btn.setToolTip("Delete use case")
        del_btn.setFixedSize(28, 28)
        del_btn.setStyleSheet(
            "color: #ef4444; border: none; font-size: 14px; background: transparent;"
        )
        del_btn.clicked.connect(lambda _, _id=uc.id, _name=uc.name: self._delete_use_case(_id, _name))
        hbox.addWidget(del_btn)

        return frame

    def _create_use_case(self) -> None:
        name = self._name_input.text().strip()
        if not name:
            return

        now = datetime.now(timezone.utc).isoformat()
        uc_id = uuid.uuid4().hex[:8]
        uc = UseCase(
            id=uc_id,
            name=name,
            created_at=now,
            updated_at=now,
        )
        # Initialise modules
        from app.engine.questionnaire_engine import compute_impacts
        result = compute_impacts(uc.answers)
        apply_impacts_to_modules(uc, result)

        json_store.save(uc)
        self._name_input.clear()
        self.refresh()
        self.open_use_case.emit(uc_id)

    def _delete_use_case(self, use_case_id: str, name: str) -> None:
        reply = QMessageBox.question(
            self,
            "Delete use case",
            f"Delete '{name}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            json_store.delete(use_case_id)
            self.refresh()
