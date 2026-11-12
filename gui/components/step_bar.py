"""
StepBar — a row of numbered steps that shows where the user is in a flow.
The current step is filled, finished steps are green with a check, locked steps are dimmed.
"""

from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QWidget

_STYLES = {
    "current": "background: #162759; color: white; border: none;",
    "done":    "background: #dcfce7; color: #166534; border: 1px solid #86efac;",
    "todo":    "background: white; color: #334155; border: 1px solid #cbd5e1;",
    "locked":  "background: #f1f5f9; color: #94a3b8; border: 1px dashed #cbd5e1;",
}


class StepBar(QWidget):
    step_clicked = Signal(int)

    def __init__(self, labels: Sequence[str], parent=None) -> None:
        super().__init__(parent)
        self._labels = list(labels)
        self._buttons: list[QPushButton] = []
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        row.addStretch()
        for index in range(len(self._labels)):
            if index:
                line = QFrame()
                line.setFixedSize(48, 2)
                line.setStyleSheet("background: #cbd5e1;")
                row.addWidget(line)
            button = QPushButton()
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _=False, i=index: self.step_clicked.emit(i))
            row.addWidget(button)
            self._buttons.append(button)
        row.addStretch()
        self.update_steps(0, done=[False] * len(self._labels), locked=[False] * len(self._labels))

    def update_steps(
        self, current: int, done: Sequence[bool], locked: Sequence[bool], locked_tip: str = "",
    ) -> None:
        for index, button in enumerate(self._buttons):
            if index == current:
                state = "current"
            elif locked[index]:
                state = "locked"
            elif done[index]:
                state = "done"
            else:
                state = "todo"
            check = "✓  " if state == "done" else ""
            button.setText(f"{check}{index + 1}  {self._labels[index]}")
            button.setToolTip(locked_tip if state == "locked" else "")
            button.setStyleSheet(
                f"QPushButton {{ {_STYLES[state]} border-radius: 16px; padding: 7px 22px; "
                "font-weight: bold; font-size: 13px; }"
            )
