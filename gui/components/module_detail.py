"""
ModuleDetail — modal dialog showing a single module's impacts, flags,
and action buttons (Acknowledge, Validate, Compute, Deploy).

Lifecycle buttons shown based on module status:
  needs_action  → Acknowledge flags → Mark Validated
  validated     → Compute
  computed      → Deploy
  computing     → (progress, no buttons)
  deployed      → Re-deploy
  deploy_failed → Re-deploy
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame, QTextEdit, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from app.models.use_case import ModuleState

_ACTION_COLOURS = {
    "retrain":     ("#7c3aed", "#ede9fe"),   # purple
    "reconfigure": ("#ea580c", "#ffedd5"),   # orange
    "review":      ("#6b7280", "#f3f4f6"),   # gray
}

_FLAG_STYLES = {
    "error":          ("#fca5a5", "#991b1b"),
    "warning":        ("#fcd34d", "#92400e"),
    "human_oversight":("#99f6e4", "#0f766e"),
}

_STATUS_STYLE = {
    "ok":            ("No action required", "#f3f4f6", "#374151"),
    "needs_action":  ("Action required", "#fef3c7", "#92400e"),
    "validated":     ("Validated — ready to compute", "#d1fae5", "#065f46"),
    "computing":     ("Computing…", "#dbeafe", "#1e40af"),
    "computed":      ("Computed — ready to deploy", "#d1fae5", "#065f46"),
    "compute_failed":("Compute failed", "#fee2e2", "#991b1b"),
    "deploying":     ("Deploying…", "#dbeafe", "#1e40af"),
    "deployed":      ("Deployed", "#d1fae5", "#065f46"),
    "deploy_failed": ("Deploy failed", "#fee2e2", "#991b1b"),
}


class ModuleDetail(QDialog):
    # Emitted when user requests an action; parent handles async work
    action_requested = Signal(str, str)   # (module_id, action)
    # action: "acknowledge" | "validate" | "compute" | "deploy"

    def __init__(self, module: ModuleState, parent=None) -> None:
        super().__init__(parent)
        self._module = module
        self.setWindowTitle(module.module_name)
        self.setMinimumSize(600, 500)
        self.setModal(True)
        self._build_ui()

    def refresh(self, module: ModuleState) -> None:
        """Update the dialog in-place after an action has been taken."""
        self._module = module
        # Rebuild only the dynamic part (status + scroll + footer)
        # The root layout items: 0=header, 1=desc, 2=status_banner, 3=scroll, 4=footer
        root = self.layout()
        for idx in (4, 3, 2):          # remove in reverse order
            item = root.takeAt(idx)
            if item and item.widget():
                item.widget().deleteLater()
        self._insert_dynamic_widgets(root)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)

        # Header (static — never changes)
        header = QHBoxLayout()
        title = QLabel(self._module.module_name)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(title)
        sub = QLabel(f"<small style='color:#6b7280'>{self._module.module_id}</small>")
        sub.setTextFormat(Qt.TextFormat.RichText)
        header.addWidget(sub)
        header.addStretch()
        root.addLayout(header)

        desc = QLabel(self._module.description)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #6b7280; font-size: 12px;")
        root.addWidget(desc)

        self._insert_dynamic_widgets(root)

    def _insert_dynamic_widgets(self, root) -> None:
        """Build (or rebuild) status banner + scroll area + footer."""
        # Status banner
        status_text, bg, fg = _STATUS_STYLE.get(
            self._module.status, ("Unknown", "#f3f4f6", "#374151")
        )
        banner = QLabel(f"Status: {status_text}")
        banner.setStyleSheet(
            f"background: {bg}; color: {fg}; padding: 6px 10px; "
            "border-radius: 4px; font-weight: bold;"
        )
        root.addWidget(banner)

        # Scroll area for impacts + flags
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setSpacing(8)

        if self._module.impacts:
            section_lbl = QLabel("Required actions")
            section_lbl.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 4px;")
            inner_layout.addWidget(section_lbl)
            for impact in self._module.impacts:
                inner_layout.addWidget(self._build_impact_card(impact))

        if self._module.flags:
            section_lbl2 = QLabel("Flags")
            section_lbl2.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 8px;")
            inner_layout.addWidget(section_lbl2)
            for flag in self._module.flags:
                inner_layout.addWidget(self._build_flag_card(flag))

        if not self._module.impacts and not self._module.flags:
            no_action = QLabel("No impacts or flags for this module with the current configuration.")
            no_action.setStyleSheet("color: #6b7280; padding: 8px;")
            inner_layout.addWidget(no_action)

        inner_layout.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll, stretch=1)

        root.addWidget(self._build_footer())

    def _build_impact_card(self, impact) -> QWidget:
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("border: 1px solid #e5e7eb; border-radius: 6px; padding: 8px;")
        vbox = QVBoxLayout(frame)
        vbox.setSpacing(4)

        top = QHBoxLayout()
        char_lbl = QLabel(impact.characteristic)
        char_lbl.setStyleSheet("font-weight: 600;")
        top.addWidget(char_lbl)
        top.addStretch()

        fg, bg = _ACTION_COLOURS.get(impact.action_type, ("#374151", "#f3f4f6"))
        badge = QLabel(impact.action_type.upper())
        badge.setStyleSheet(
            f"background: {bg}; color: {fg}; border-radius: 3px; "
            "padding: 1px 6px; font-size: 10px; font-weight: bold;"
        )
        top.addWidget(badge)
        vbox.addLayout(top)

        affects = QLabel(f"Affects: {impact.affects}")
        affects.setStyleSheet("color: #6b7280; font-size: 11px;")
        vbox.addWidget(affects)

        what = QLabel(impact.what_changes)
        what.setWordWrap(True)
        what.setStyleSheet("font-size: 12px;")
        vbox.addWidget(what)

        reason = QLabel(f"Triggered by: {impact.reason}")
        reason.setStyleSheet("color: #9ca3af; font-size: 11px;")
        vbox.addWidget(reason)

        return frame

    def _build_flag_card(self, flag) -> QWidget:
        bg, fg = _FLAG_STYLES.get(flag.type, ("#f3f4f6", "#374151"))
        frame = QFrame()
        frame.setStyleSheet(
            f"background: {bg}; border-radius: 6px; padding: 8px;"
        )
        hbox = QHBoxLayout(frame)
        msg = QLabel(flag.message)
        msg.setWordWrap(True)
        msg.setStyleSheet(f"color: {fg}; font-size: 12px;")
        hbox.addWidget(msg, stretch=1)
        if flag.acknowledged:
            ack = QLabel("Acknowledged")
            ack.setStyleSheet("color: #6b7280; font-size: 11px; font-style: italic;")
            hbox.addWidget(ack)
        return frame

    def _build_footer(self) -> QWidget:
        bar = QWidget()
        hbox = QHBoxLayout(bar)
        hbox.setContentsMargins(0, 4, 0, 0)
        hbox.addStretch()

        status = self._module.status
        unacked = sum(1 for f in self._module.flags if not f.acknowledged)

        if status == "needs_action":
            if unacked > 0:
                btn = QPushButton(f"Acknowledge {unacked} flag(s)")
                btn.setStyleSheet("background: #ef4444; color: white; padding: 6px 14px; border-radius: 4px;")
                btn.clicked.connect(lambda: self.action_requested.emit(self._module.module_id, "acknowledge"))
                hbox.addWidget(btn)
            else:
                btn = QPushButton("Mark as Validated")
                btn.setStyleSheet("background: #0d9488; color: white; padding: 6px 14px; border-radius: 4px;")
                btn.clicked.connect(lambda: self.action_requested.emit(self._module.module_id, "validate"))
                hbox.addWidget(btn)

        elif status == "validated":
            btn = QPushButton("Run Compute")
            btn.setStyleSheet("background: #2563eb; color: white; padding: 6px 14px; border-radius: 4px;")
            btn.clicked.connect(lambda: self.action_requested.emit(self._module.module_id, "compute"))
            hbox.addWidget(btn)

        elif status in ("computed", "deploy_failed"):
            btn = QPushButton("Deploy to ROS 2")
            btn.setStyleSheet("background: #16a34a; color: white; padding: 6px 14px; border-radius: 4px;")
            btn.clicked.connect(lambda: self.action_requested.emit(self._module.module_id, "deploy"))
            hbox.addWidget(btn)

        elif status == "deployed":
            btn = QPushButton("Re-deploy to ROS 2")
            btn.setStyleSheet("background: #16a34a; color: white; padding: 6px 14px; border-radius: 4px;")
            btn.clicked.connect(lambda: self.action_requested.emit(self._module.module_id, "deploy"))
            hbox.addWidget(btn)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("padding: 6px 14px; border-radius: 4px;")
        close_btn.clicked.connect(self.accept)
        hbox.addWidget(close_btn)

        return bar
