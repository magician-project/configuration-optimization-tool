"""
app/main.py — entry point for the Configuration Optimization Tool desktop app.

Run with:
    python app/main.py
    (or from the repo root: python -m app.main)
"""

import sys
import os
import logging

# Ensure the repo root is on sys.path so `app`, `gui`, and `modules` are importable
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from gui.main_window import MainWindow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Configuration Optimization Tool")
    app.setOrganizationName("MAGICIAN")

    # Base font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Global stylesheet
    app.setStyleSheet("""
        QWidget {
            font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
        }
        QMainWindow, QStackedWidget {
            background: #f0f2f5;
        }
        QPushButton {
            border: 1px solid #d1d5db;
            border-radius: 5px;
            padding: 5px 14px;
            background: #ffffff;
            color: #374151;
            font-size: 12px;
        }
        QPushButton:hover {
            background: #f3f4f6;
            border-color: #9ca3af;
        }
        QPushButton:pressed {
            background: #e5e7eb;
        }
        QPushButton:disabled {
            color: #9ca3af;
            background: #f9fafb;
            border-color: #e5e7eb;
        }
        QComboBox {
            border: 1px solid #d1d5db;
            border-radius: 5px;
            padding: 5px 10px;
            background: white;
            color: #111827;
            selection-background-color: #162759;
        }
        QComboBox:hover { border-color: #162759; }
        QComboBox:focus { border-color: #162759; }
        QComboBox::drop-down {
            border: none;
            width: 24px;
        }
        QComboBox QAbstractItemView {
            border: 1px solid #d1d5db;
            border-radius: 4px;
            background: white;
            color: #111827;
            selection-background-color: #162759;
            selection-color: white;
            outline: 0px;
        }
        QComboBox QAbstractItemView::item {
            background: white;
            color: #111827;
            padding: 4px 10px;
        }
        QComboBox QAbstractItemView::item:selected {
            background: #162759;
            color: white;
        }
        QLineEdit, QSpinBox, QDoubleSpinBox {
            border: 1px solid #d1d5db;
            border-radius: 5px;
            padding: 5px 8px;
            background: white;
            color: #111827;
        }
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
            border-color: #162759;
        }
        QCheckBox {
            spacing: 8px;
            color: #374151;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border: 2px solid #d1d5db;
            border-radius: 3px;
            background: white;
        }
        QCheckBox::indicator:checked {
            background: #162759;
            border-color: #162759;
        }
        QGroupBox {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            background: white;
            margin-top: 12px;
            padding: 8px 12px 12px 12px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 14px;
            padding: 0 6px;
            color: #162759;
            font-size: 12px;
            font-weight: bold;
        }
        QTabWidget::pane {
            border: 1px solid #e5e7eb;
            border-top: none;
            background: #f0f2f5;
        }
        QTabBar::tab {
            padding: 8px 22px;
            border: 1px solid #e5e7eb;
            border-bottom: none;
            border-radius: 6px 6px 0 0;
            background: #e9ecef;
            color: #6b7280;
            margin-right: 3px;
            font-size: 12px;
            font-weight: 600;
        }
        QTabBar::tab:selected {
            background: #162759;
            color: white;
            border-color: #162759;
        }
        QTabBar::tab:hover:!selected {
            background: #d1d5db;
            color: #374151;
        }
        QScrollBar:vertical {
            border: none;
            background: #f0f2f5;
            width: 8px;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background: #c4c9d4;
            border-radius: 4px;
            min-height: 30px;
        }
        QScrollBar::handle:vertical:hover {
            background: #9ca3af;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
        QToolTip {
            background: #1f2937;
            color: white;
            border: none;
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 11px;
        }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
