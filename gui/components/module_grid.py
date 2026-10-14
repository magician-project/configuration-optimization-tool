"""
ModuleGrid — shows all 6 modules as clickable tiles with status colours.
Emits module_selected(module_id) when a tile is clicked.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QGridLayout, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QSizePolicy, QGraphicsDropShadowEffect, QPushButton,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from app.models.use_case import ModuleState
from app.engine.module_registry import MODULES

# (strip_colour, accent/text, status label)
# The tile itself always uses a white background + thin grey border.
# Only the 3-px top strip changes colour with status.
_STATUS_STYLE = {
    "ok":            ("#d1d5db", "#6b7280", "No action needed"),
    "needs_action":  ("#f59e0b", "#b45309", "Action required"),
    "validated":     ("#34d399", "#15803d", "Validated"),
    "computing":     ("#60a5fa", "#1d4ed8", "Computing…"),
    "computed":      ("#34d399", "#15803d", "Ready to deploy"),
    "compute_failed": ("#f87171", "#b91c1c", "Compute failed"),
    "deploying":     ("#60a5fa", "#1d4ed8", "Deploying…"),
    "deployed":      ("#10b981", "#065f46", "Deployed"),
    "deploy_failed": ("#f87171", "#b91c1c", "Deploy failed"),
    "disabled":      ("#9ca3af", "#4b5563", "Disabled"),
}

_ACTION_TYPE_COLOURS = {
    "retrain":     ("#6d28d9", "#ede9fe"),
    "reconfigure": ("#c2410c", "#ffedd5"),
    "review":      ("#374151", "#f3f4f6"),
}

MODULE_ORDER = ["grabber", "orienteering_solver", "localiser", "tactile_sensor", "vision_classifier", "ergodic_control", "motion_planning"]


class ModuleGrid(QWidget):
    module_selected = Signal(str)   # module_id
    override_toggle_requested = Signal(str)   # module_id
    override_reset_requested = Signal(str)   # module_id

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._tiles: dict[str, _ModuleTile] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(10)

        # Summary strip
        summary_frame = QFrame()
        summary_frame.setStyleSheet(
            "background: white; border: 1px solid #e5e7eb; border-radius: 6px; padding: 4px 14px;"
        )
        summary_layout = QHBoxLayout(summary_frame)
        summary_layout.setContentsMargins(0, 4, 0, 4)
        self._summary_lbl = QLabel("Loading…")
        self._summary_lbl.setStyleSheet("color: #6b7280; font-size: 12px;")
        summary_layout.addWidget(self._summary_lbl)
        summary_layout.addStretch()
        hint = QLabel("Click a tile to manage")
        hint.setStyleSheet("color: #9ca3af; font-size: 11px;")
        summary_layout.addWidget(hint)
        vbox.addWidget(summary_frame)

        # Tile grid: 3 columns
        grid = QGridLayout()
        grid.setSpacing(12)
        for i, mid in enumerate(MODULE_ORDER):
            info = MODULES[mid]
            tile = _ModuleTile(mid, info["name"], info["description"])
            tile.clicked.connect(lambda _mid=mid: self.module_selected.emit(_mid))
            tile.toggle_requested.connect(lambda _mid=mid: self.override_toggle_requested.emit(_mid))
            tile.reset_requested.connect(lambda _mid=mid: self.override_reset_requested.emit(_mid))
            self._tiles[mid] = tile
            grid.addWidget(tile, i // 3, i % 3)

        # Stretch last row so tiles align top
        grid.setRowStretch(2, 1)
        vbox.addLayout(grid, stretch=1)

    def update_modules(
        self,
        modules: dict,
        default_modules: Optional[List[str]] = None,
        module_overrides: Optional[Dict[str, bool]] = None,
    ) -> None:
        default_modules = default_modules or []
        module_overrides = module_overrides or {}
        needs = validated = deployed = 0
        for mid, tile in self._tiles.items():
            ms: ModuleState | None = modules.get(mid)
            if ms:
                tile.update_state(ms, in_default=mid in default_modules, override=module_overrides.get(mid))
                if ms.status == "needs_action":
                    needs += 1
                elif ms.status in ("validated", "computed"):
                    validated += 1
                elif ms.status == "deployed":
                    deployed += 1

        parts = []
        if needs:
            parts.append(f"{needs} module{'s' if needs > 1 else ''} need action")
        if validated:
            parts.append(f"{validated} validated")
        if deployed:
            parts.append(f"{deployed} deployed")
        if not parts:
            parts.append("All modules up to date")
        self._summary_lbl.setText("   |   ".join(parts))


class _ModuleTile(QFrame):
    clicked = Signal()
    toggle_requested = Signal()
    reset_requested = Signal()

    _NORMAL_BORDER = "#e5e7eb"

    def __init__(self, module_id: str, name: str, description: str, parent=None) -> None:
        super().__init__(parent)
        self._module_id = module_id
        self._name = name
        self._description = description
        self._strip_colour = "#d1d5db"
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(145)
        self.setMaximumHeight(210)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._build_ui()
        self._set_border(self._NORMAL_BORDER)
        self._apply_shadow(blur=10, offset=2, alpha=18)

    def _apply_shadow(self, blur: int, offset: int, alpha: int) -> None:
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(blur)
        shadow.setOffset(0, offset)
        shadow.setColor(QColor(0, 0, 0, alpha))
        self.setGraphicsEffect(shadow)

    def _set_border(self, colour: str) -> None:
        self.setStyleSheet(
            "QFrame { background: white; border: none; border-radius: 8px; }"
        )

    def _build_ui(self) -> None:
        # Outer layout has no margins — top strip sits flush to rounded corners
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Coloured top strip (3 px)
        self._strip = QFrame()
        self._strip.setFixedHeight(3)
        self._strip.setStyleSheet(
            f"background: {self._strip_colour}; border-radius: 7px 7px 0 0; border: none;"
        )
        outer.addWidget(self._strip)

        # Content area
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(14, 10, 14, 10)
        vbox.setSpacing(5)
        outer.addWidget(content, stretch=1)

        # Top: name + flag badge
        header = QHBoxLayout()
        header.setSpacing(8)

        name_lbl = QLabel(self._name)
        name_lbl.setStyleSheet("font-weight: 600; font-size: 13px; background: transparent; color: #111827;")
        header.addWidget(name_lbl, stretch=1)

        self._flag_badge = QLabel()
        self._flag_badge.setStyleSheet(
            "background: #ef4444; color: white; border-radius: 8px; "
            "padding: 0px 6px; font-size: 10px; font-weight: bold; border: none;"
        )
        self._flag_badge.hide()
        header.addWidget(self._flag_badge)

        self._override_btn = QPushButton()
        self._override_btn.setCheckable(True)
        self._override_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._override_btn.setFixedWidth(40)
        self._override_btn.clicked.connect(self._on_override_toggled)
        header.addWidget(self._override_btn)
        vbox.addLayout(header)

        # Status label + reset-override link (link only shown when an
        # explicit override exists for this module)
        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        self._status_lbl = QLabel("ok")
        self._status_lbl.setStyleSheet("font-size: 11px; color: #6b7280; background: transparent;")
        status_row.addWidget(self._status_lbl)
        self._reset_link = QPushButton("Reset")
        self._reset_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_link.setStyleSheet(
            "QPushButton { border: none; background: transparent; color: #2563eb; "
            "font-size: 10px; text-decoration: underline; padding: 0; }"
        )
        self._reset_link.setToolTip(
            "Clear this manual override — the module will follow the task-type default again."
        )
        self._reset_link.clicked.connect(lambda: self.reset_requested.emit())
        self._reset_link.hide()
        status_row.addWidget(self._reset_link)
        status_row.addStretch()
        vbox.addLayout(status_row)

        # Default-scope badge (shown only when the module is outside the
        # task-type default set, or explicitly enabled despite that)
        self._scope_badge = QLabel()
        self._scope_badge.hide()
        vbox.addWidget(self._scope_badge)

        # Action type badges row
        self._badges_row = QHBoxLayout()
        self._badges_row.setSpacing(4)
        self._badges_row.setContentsMargins(0, 2, 0, 2)
        vbox.addLayout(self._badges_row)

        # Impacts summary
        self._impacts_lbl = QLabel()
        self._impacts_lbl.setStyleSheet(
            "font-size: 11px; color: #6b7280; background: transparent;"
        )
        self._impacts_lbl.setWordWrap(True)
        vbox.addWidget(self._impacts_lbl)

        vbox.addStretch()

        # Footer hint
        hint = QLabel("Click to manage")
        hint.setStyleSheet("font-size: 10px; color: #d1d5db; background: transparent;")
        hint.setAlignment(Qt.AlignmentFlag.AlignRight)
        vbox.addWidget(hint)

    def update_state(
        self, ms: ModuleState, in_default: bool = True, override: Optional[bool] = None
    ) -> None:
        strip, accent, status_text = _STATUS_STYLE.get(
            ms.status, ("#d1d5db", "#6b7280", ms.status)
        )
        self._strip_colour = strip
        self._strip.setStyleSheet(
            f"background: {strip}; border-radius: 7px 7px 0 0; border: none;"
        )
        self._set_border(self._NORMAL_BORDER)
        self._status_lbl.setText(status_text)
        self._status_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {accent}; background: transparent;"
        )
        self._reset_link.setVisible(override is not None)

        # Override toggle — reflects current state, blocked while a job is in flight.
        # Colour + text coded (ON = green, OFF = grey) rather than a native
        # checkbox glyph, which was too subtle to read at a glance.
        is_enabled = ms.status != "disabled"
        self._override_btn.blockSignals(True)
        self._override_btn.setChecked(is_enabled)
        self._override_btn.blockSignals(False)
        self._override_btn.setEnabled(ms.status not in ("computing", "deploying"))
        if is_enabled:
            self._override_btn.setText("ON")
            self._override_btn.setStyleSheet(
                "QPushButton { background: #16a34a; color: white; border: none; "
                "border-radius: 9px; padding: 2px 0; font-size: 10px; font-weight: bold; }"
                "QPushButton:disabled { background: #86efac; color: #f0fdf4; }"
            )
            self._override_btn.setToolTip(
                "Module is enabled — click to disable it (no impacts, flags, compute or deploy)."
            )
        else:
            self._override_btn.setText("OFF")
            self._override_btn.setStyleSheet(
                "QPushButton { background: #9ca3af; color: white; border: none; "
                "border-radius: 9px; padding: 2px 0; font-size: 10px; font-weight: bold; }"
                "QPushButton:disabled { background: #d1d5db; color: #f9fafb; }"
            )
            self._override_btn.setToolTip("Module is disabled — click to re-enable it.")

        # Scope badge: a module outside the default set is "disabled" by
        # default (see resolve_effective_overrides), so the only way to see
        # this badge is an explicit override forcing it on anyway.
        if ms.status != "disabled" and not in_default and override is True:
            self._scope_badge.setText("ENABLED (OVERRIDE)")
            self._scope_badge.setStyleSheet(
                "background: #dbeafe; color: #1d4ed8; border-radius: 4px; "
                "padding: 1px 7px; font-size: 10px; font-weight: bold;"
            )
            self._scope_badge.setToolTip(
                "Manually enabled even though it isn't in the default module set for this task type."
            )
            self._scope_badge.show()
        else:
            self._scope_badge.hide()

        # Flag badge
        unacked = sum(1 for f in ms.flags if not f.acknowledged)
        if unacked:
            has_error = any(f.type == "error" and not f.acknowledged for f in ms.flags)
            badge_bg = "#ef4444" if has_error else "#f59e0b"
            self._flag_badge.setText(f"{unacked} flag{'s' if unacked > 1 else ''}")
            self._flag_badge.setStyleSheet(
                f"background: {badge_bg}; color: white; border-radius: 9px; "
                "padding: 1px 7px; font-size: 10px; font-weight: bold;"
            )
            self._flag_badge.show()
        else:
            self._flag_badge.hide()


        # Clear + rebuild action type badges
        while self._badges_row.count():
            item = self._badges_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        seen: set[str] = set()
        for imp in ms.impacts:
            at = imp.action_type
            if at not in seen:
                seen.add(at)
                fg_b, bg_b = _ACTION_TYPE_COLOURS.get(at, ("#374151", "#f3f4f6"))
                badge = QLabel(at.upper())
                badge.setStyleSheet(
                    f"background: {bg_b}; color: {fg_b}; border-radius: 4px; "
                    "padding: 1px 7px; font-size: 10px; font-weight: bold;"
                )
                self._badges_row.addWidget(badge)
        self._badges_row.addStretch()

        # Impacts summary text
        if ms.impacts:
            lines = [f"·  {i.characteristic}" for i in ms.impacts[:2]]
            if len(ms.impacts) > 2:
                lines.append(f"   +{len(ms.impacts) - 2} more")
            self._impacts_lbl.setText("\n".join(lines))
        else:
            self._impacts_lbl.setText(
                self._description[:70] + "…" if len(self._description) > 70 else self._description
            )

    def enterEvent(self, event) -> None:
        self._apply_shadow(blur=22, offset=5, alpha=35)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._apply_shadow(blur=10, offset=2, alpha=18)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)

    def _on_override_toggled(self, _checked: bool) -> None:
        # The parent derives the actual new value from the authoritative
        # use case state, not from this button's transient UI state.
        self.toggle_requested.emit()
