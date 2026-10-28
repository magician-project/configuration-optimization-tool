"""Info button shared by the questionnaire questions and the configuration validation."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton


def make_info_button(object_name: str, tooltip: str) -> QPushButton:
    """Round neutral "i" button; the caller connects `clicked` to the panel it opens."""
    button = QPushButton("i")
    button.setObjectName(object_name)
    button.setToolTip(tooltip)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setFixedSize(16, 16)
    button.setStyleSheet(
        "QPushButton { color: #475569; background: white; border: 1px solid #cbd5e1; "
        "border-radius: 8px; font-size: 10px; font-weight: bold; padding: 0; } "
        "QPushButton:hover { color: #1e293b; background: #f1f5f9; border-color: #94a3b8; }"
    )
    return button
