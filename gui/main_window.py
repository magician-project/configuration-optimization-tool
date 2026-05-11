"""
MainWindow — top-level QMainWindow for the Configuration Optimization Tool.
Manages navigation between the Home page and individual Use Case pages.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget,
)
from PySide6.QtCore import Qt

from gui.pages.home_page import HomePage
from gui.pages.use_case_page import UseCasePage

_HEADER_STYLE = (
    "background: #162759; color: white; padding: 10px 24px;"
)
_FOOTER_STYLE = (
    "background: #162759; color: #9eb3d0; padding: 6px 24px; font-size: 11px;"
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Configuration Optimization Tool — MAGICIAN")
        self.setMinimumSize(960, 680)
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet(_HEADER_STYLE)
        header.setFixedHeight(56)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(24, 0, 24, 0)

        logo = QLabel("MAGICIAN")
        logo.setStyleSheet("font-size: 18px; font-weight: 900; letter-spacing: 2px; color: white;")
        h_layout.addWidget(logo)

        sep = QLabel("|")
        sep.setStyleSheet("color: #4a6fa5; margin: 0 10px;")
        h_layout.addWidget(sep)

        title = QLabel("Configuration Optimization Tool")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #c8d8ea;")
        h_layout.addWidget(title)
        h_layout.addStretch()
        root.addWidget(header)

        # Page stack
        self._stack = QStackedWidget()
        self._home_page = HomePage()
        self._home_page.open_use_case.connect(self._open_use_case)
        self._stack.addWidget(self._home_page)   # index 0
        root.addWidget(self._stack, stretch=1)

        # Footer
        footer = QWidget()
        footer.setStyleSheet(_FOOTER_STYLE)
        footer.setFixedHeight(30)
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(24, 0, 24, 0)
        f_layout.addWidget(QLabel("MAGICIAN — EU Horizon 2020 Project"))
        f_layout.addStretch()
        f_layout.addWidget(QLabel("ROS 2 · Python · COT"))
        root.addWidget(footer)

    def _open_use_case(self, use_case_id: str) -> None:
        # Remove any existing use-case page (index 1+)
        while self._stack.count() > 1:
            w = self._stack.widget(1)
            self._stack.removeWidget(w)
            w.deleteLater()

        page = UseCasePage(use_case_id)
        page.navigate_home.connect(self._go_home)
        self._stack.addWidget(page)
        self._stack.setCurrentIndex(1)

    def _go_home(self) -> None:
        self._home_page.refresh()
        self._stack.setCurrentIndex(0)
        # Clean up use case page
        while self._stack.count() > 1:
            w = self._stack.widget(1)
            self._stack.removeWidget(w)
            w.deleteLater()
