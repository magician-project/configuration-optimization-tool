"""QuestionHelpDialog — panel behind a question's `?` icon: short summary, optional detail sections."""

from __future__ import annotations

import re
from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QTextBrowser, QVBoxLayout


def _escape_markdown(text: str) -> str:
    return re.sub(r"([\\`*_{}\[\]()#+!|<>~-])", r"\\\1", text)


class QuestionHelpDialog(QDialog):
    # (module_id, readme_anchor) — emitted when the user follows the documentation link
    documentation_requested = Signal(str, str)

    def __init__(
        self, title: str, summary: str, details: Optional[str] = None,
        help_link: Optional[dict] = None, parent=None,
    ) -> None:
        """`summary` is plain text (the tooltip); `details` is markdown shown below it."""
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(460, 320)

        root = QVBoxLayout(self)
        body = QTextBrowser()
        markdown = _escape_markdown(summary)
        if details:
            markdown += "\n\n" + details
        body.setMarkdown(markdown)
        root.addWidget(body, stretch=1)

        buttons = QHBoxLayout()
        buttons.addStretch()
        if help_link:
            doc_btn = QPushButton("Open documentation")
            doc_btn.setObjectName("open_documentation")
            doc_btn.clicked.connect(
                lambda: self._request_documentation(help_link["module"], help_link["anchor"])
            )
            buttons.addWidget(doc_btn)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        buttons.addWidget(close_btn)
        root.addLayout(buttons)

    def _request_documentation(self, module_id: str, anchor: str) -> None:
        self.close()
        self.documentation_requested.emit(module_id, anchor)
