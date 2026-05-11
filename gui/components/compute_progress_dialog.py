"""
ComputeProgressDialog — shows live stdout from the compute subprocess.
Opened by use_case_page.py when the user clicks "Run Compute".
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout,
)
from PySide6.QtCore import Qt, Slot


class ComputeProgressDialog(QDialog):
    def __init__(self, module_name: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Computing — {module_name}")
        self.setMinimumSize(560, 380)
        self.setModal(True)

        root = QVBoxLayout(self)

        self._status_lbl = QLabel(f"Running computation for {module_name}…")
        self._status_lbl.setStyleSheet("font-weight: bold;")
        root.addWidget(self._status_lbl)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setStyleSheet(
            "background: #111827; color: #d1fae5; font-family: monospace; font-size: 12px;"
        )
        root.addWidget(self._log, stretch=1)

        footer = QHBoxLayout()
        footer.addStretch()
        self._close_btn = QPushButton("Close")
        self._close_btn.setEnabled(False)
        self._close_btn.clicked.connect(self.accept)
        footer.addWidget(self._close_btn)
        root.addLayout(footer)

    @Slot(str)
    def append_line(self, line: str) -> None:
        self._log.append(line)

    @Slot(bool, object)
    def on_done(self, success: bool, result_path: str | None) -> None:
        if success:
            self._status_lbl.setText("Computation completed successfully.")
            self._status_lbl.setStyleSheet("font-weight: bold; color: #16a34a;")
        else:
            self._status_lbl.setText("Computation failed. See log above.")
            self._status_lbl.setStyleSheet("font-weight: bold; color: #dc2626;")
        self._close_btn.setEnabled(True)
