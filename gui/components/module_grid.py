"""
ModuleGrid — shows all 6 modules as clickable tiles with status colours.
Emits module_selected(module_id) when a tile is clicked.
"""

from __future__ import annotations

import math

from PySide6.QtWidgets import (
    QWidget, QGridLayout, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QSizePolicy, QGraphicsDropShadowEffect, QScrollArea,
)
from PySide6.QtCore import Qt, Signal, QEvent, QLineF, QPoint, QPointF, QRect, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF

from app.models.use_case import ModuleState
from app.engine.module_dependencies import GroupEdge, VisibleEdge, visible_dependency_edges, visible_group_edges
from app.engine.module_registry import MODULE_GROUPS, MODULES, group_of

# (strip_colour, accent/text, status label)
# In-scope tiles are white with a status-coloured top strip; out-of-scope tiles are
# flat grey with muted text (see _ModuleTile.update_state).
_STATUS_STYLE = {
    "ok":            ("#93c5fd", "#1d4ed8", "Ready to validate"),
    "not_assessed":  ("#d1d5db", "#6b7280", "Not assessed"),
    "needs_action":  ("#f59e0b", "#b45309", "Action required"),
    "validated":     ("#34d399", "#15803d", "Validated"),
    "computing":     ("#60a5fa", "#1d4ed8", "Computing…"),
    "computed":      ("#34d399", "#15803d", "Ready to deploy"),
    "compute_failed": ("#f87171", "#b91c1c", "Compute failed"),
    "deploying":     ("#60a5fa", "#1d4ed8", "Deploying…"),
    "deployed":      ("#10b981", "#065f46", "Deployed"),
    "deploy_failed": ("#f87171", "#b91c1c", "Deploy failed"),
    "out_of_scope":  ("#cbd5e1", "#9ca3af", "Out of scope"),
}

_ACTION_TYPE_COLOURS = {
    "retrain":     ("#6d28d9", "#ede9fe"),
    "reconfigure": ("#c2410c", "#ffedd5"),
    "review":      ("#374151", "#f3f4f6"),
}

class _DependencyArrows(QWidget):
    """Transparent overlay painting provider -> consumer arrows over the tiles and group frames."""

    _COLOUR = QColor("#6b7280")
    _UNVERIFIED_COLOUR = QColor("#9ca3af")

    def __init__(self, tiles: dict, group_frames: dict, parent: QWidget) -> None:
        super().__init__(parent)
        self._tiles = tiles
        self._group_frames = group_frames
        self._edges: list[VisibleEdge] = []
        self._group_edges: list[GroupEdge] = []
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet("background: transparent;")
        parent.installEventFilter(self)
        for widget in (*tiles.values(), *group_frames.values()):
            widget.installEventFilter(self)

    def set_edges(self, edges: list[VisibleEdge], group_edges: list[GroupEdge]) -> None:
        self._edges = edges
        self._group_edges = group_edges
        self.update()

    def eventFilter(self, obj, event) -> bool:
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Move, QEvent.Type.Show):
            if obj is self.parentWidget():
                self.setGeometry(self.parentWidget().rect())
            self.raise_()
            self.update()
        return False

    def _rect_of(self, widget: QWidget) -> QRectF:
        """Widget rectangle in the overlay's coordinates (tiles sit inside group frames)."""
        return QRectF(QRect(widget.mapTo(self.parentWidget(), QPoint(0, 0)), widget.size()))

    @staticmethod
    def _border_point(rect: QRectF, towards: QPointF) -> QPointF:
        """Where the line from the rect's centre to `towards` leaves the rect."""
        centre = rect.center()
        dx, dy = towards.x() - centre.x(), towards.y() - centre.y()
        if dx == 0 and dy == 0:
            return centre
        scale = min(
            (rect.width() / 2) / abs(dx) if dx else float("inf"),
            (rect.height() / 2) / abs(dy) if dy else float("inf"),
        )
        return QPointF(centre.x() + dx * scale, centre.y() + dy * scale)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for edge in self._edges:
            src, dst = self._tiles.get(edge.provider), self._tiles.get(edge.consumer)
            if src is not None and dst is not None:
                self._draw_arrow(painter, self._rect_of(src), self._rect_of(dst), edge.verified, 1.8, 8.0)
        for edge in self._group_edges:
            src, dst = self._group_frames.get(edge.provider_group), self._group_frames.get(edge.consumer_group)
            if src is not None and dst is not None:
                self._draw_arrow(painter, self._rect_of(src), self._rect_of(dst), edge.verified, 2.6, 11.0)
        painter.end()

    def _draw_arrow(
        self, painter: QPainter, src: QRectF, dst: QRectF, verified: bool, width: float, head_size: float,
    ) -> None:
        start = self._border_point(src, dst.center())
        end = self._border_point(dst, src.center())
        line = QLineF(start, end)
        if line.length() < 2:
            return
        colour = self._COLOUR if verified else self._UNVERIFIED_COLOUR
        pen = QPen(colour, width)
        pen.setStyle(Qt.PenStyle.SolidLine if verified else Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(colour)
        painter.drawLine(line)
        # Arrow head is always solid, even on a dashed line
        pen.setStyle(Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        angle = math.atan2(line.dy(), line.dx())
        painter.drawPolygon(QPolygonF([
            end,
            QPointF(end.x() - head_size * math.cos(angle - math.pi / 7),
                    end.y() - head_size * math.sin(angle - math.pi / 7)),
            QPointF(end.x() - head_size * math.cos(angle + math.pi / 7),
                    end.y() - head_size * math.sin(angle + math.pi / 7)),
        ]))


class ModuleGrid(QWidget):
    module_selected = Signal(str)   # module_id

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._tiles: dict[str, _ModuleTile] = {}
        self._group_frames: dict[str, QFrame] = {}
        self._group_grids: dict[str, QGridLayout] = {}
        self._edges: list[VisibleEdge] = []
        self._group_edges: list[GroupEdge] = []
        self._build_ui()

    def dependency_edges(self) -> list[VisibleEdge]:
        """Module arrows currently drawn (provider -> consumer, within a group)."""
        return list(self._edges)

    def group_edges(self) -> list[GroupEdge]:
        """Group arrows currently drawn between group frames."""
        return list(self._group_edges)

    def tile(self, module_id: str) -> "_ModuleTile":
        return self._tiles[module_id]

    def group_frame(self, group_id: str) -> QFrame:
        return self._group_frames[group_id]

    def tile_cell(self, module_id: str) -> tuple[int, int]:
        """(row, column) of a tile inside its group frame."""
        grid = self._group_grids[group_of(module_id)]
        row, column, _, _ = grid.getItemPosition(grid.indexOf(self._tiles[module_id]))
        return row, column

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
        legend = QLabel("Arrow: provides input to  ·  dashed = not yet verified")
        legend.setStyleSheet("color: #9ca3af; font-size: 11px;")
        summary_layout.addWidget(legend)
        vbox.addWidget(summary_frame)

        # One frame per architecture group, side by side in flow order like the MAGICIAN diagram.
        # The wide gap between frames leaves room for the group arrows; a frame is as wide as
        # the columns it holds.
        groups_layout = QHBoxLayout()
        groups_layout.setSpacing(44)
        for group_id, info in MODULE_GROUPS.items():
            groups_layout.addWidget(self._build_group_frame(group_id, info), stretch=info["columns"])

        # Scrollable so tiles keep their minimum size instead of overlapping in a small window.
        # The stretch below keeps the frames as tall as their content.
        tiles_container = QWidget()
        tiles_container.setStyleSheet("background: transparent;")
        container_layout = QVBoxLayout(tiles_container)
        container_layout.setContentsMargins(3, 3, 3, 3)
        container_layout.addLayout(groups_layout)
        container_layout.addStretch()
        self._arrows = _DependencyArrows(self._tiles, self._group_frames, tiles_container)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")
        scroll.setWidget(tiles_container)
        vbox.addWidget(scroll, stretch=1)

    def _build_group_frame(self, group_id: str, info: dict) -> QFrame:
        frame = QFrame()
        frame.setObjectName("moduleGroup")
        frame.setStyleSheet(
            "QFrame#moduleGroup { background: rgba(255, 255, 255, 120); "
            "border: 1px dashed #b8c2cf; border-radius: 10px; }"
        )
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(10, 8, 10, 10)
        frame_layout.setSpacing(6)
        title = QLabel(info["name"].upper())
        title.setStyleSheet(
            "font-size: 10px; font-weight: 700; color: #6b7280; background: transparent; border: none;"
        )
        frame_layout.addWidget(title)

        grid = QGridLayout()
        # Wide horizontal gaps leave room for the module arrows
        grid.setHorizontalSpacing(36)
        grid.setVerticalSpacing(10)
        frame_layout.addLayout(grid)

        # Fixed cells, filled column by column: tiles keep their place whatever their status
        modules = info["modules"]
        rows = -(-len(modules) // info["columns"])
        for i, module_id in enumerate(modules):
            module = MODULES[module_id]
            tile = _ModuleTile(module_id, module["name"], frame)
            tile.clicked.connect(lambda _mid=module_id: self.module_selected.emit(_mid))
            self._tiles[module_id] = tile
            grid.addWidget(tile, i % rows, i // rows)
        for col in range(info["columns"]):
            grid.setColumnStretch(col, 1)
        frame_layout.addStretch()  # keeps the tiles at the top of a frame that matches its taller neighbour
        self._group_frames[group_id] = frame
        self._group_grids[group_id] = grid
        return frame

    def update_modules(self, modules: dict) -> None:
        def is_out_of_scope(module_id: str) -> bool:
            return getattr(modules.get(module_id), "status", None) == "out_of_scope"

        # not_assessed modules are not in scope yet, so they get no arrows either
        drawn = [
            m for m in self._tiles
            if not is_out_of_scope(m) and m in modules and modules[m].status != "not_assessed"
        ]
        self._edges = visible_dependency_edges(drawn)
        self._group_edges = visible_group_edges(drawn)
        self._arrows.set_edges(self._edges, self._group_edges)

        needs = validated = deployed = not_assessed = 0
        for mid, tile in self._tiles.items():
            ms: ModuleState | None = modules.get(mid)
            if ms:
                tile.update_state(ms)
                if ms.status == "needs_action":
                    needs += 1
                elif ms.status in ("validated", "computed"):
                    validated += 1
                elif ms.status == "deployed":
                    deployed += 1
                elif ms.status == "not_assessed":
                    not_assessed += 1

        parts = []
        if needs:
            parts.append(f"{needs} module{'s' if needs > 1 else ''} need action")
        if validated:
            parts.append(f"{validated} validated")
        if deployed:
            parts.append(f"{deployed} deployed")
        if not parts:
            parts.append("Not assessed yet" if not_assessed else "All modules up to date")
        self._summary_lbl.setText("   |   ".join(parts))


class _ModuleTile(QFrame):
    clicked = Signal()

    def __init__(self, module_id: str, name: str, parent=None) -> None:
        super().__init__(parent)
        self._module_id = module_id
        self._name = name
        self._strip_colour = "#d1d5db"
        self._out_of_scope = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(84)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._build_ui()
        self._set_background("white")
        self._apply_shadow(blur=10, offset=2, alpha=18)

    def _apply_shadow(self, blur: int, offset: int, alpha: int) -> None:
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(blur)
        shadow.setOffset(0, offset)
        shadow.setColor(QColor(0, 0, 0, alpha))
        self.setGraphicsEffect(shadow)

    def _set_background(self, colour: str) -> None:
        self.setStyleSheet(
            f"QFrame {{ background: {colour}; border: none; border-radius: 8px; }}"
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
        vbox.setContentsMargins(12, 8, 12, 8)
        vbox.setSpacing(4)
        outer.addWidget(content, stretch=1)

        # Top: name + flag badge
        header = QHBoxLayout()
        header.setSpacing(8)

        self._name_lbl = QLabel(self._name)
        self._name_lbl.setWordWrap(True)
        self._name_lbl.setStyleSheet("font-weight: 600; font-size: 13px; background: transparent; color: #111827;")
        header.addWidget(self._name_lbl, stretch=1)

        self._flag_badge = QLabel()
        self._flag_badge.setStyleSheet(
            "background: #ef4444; color: white; border-radius: 8px; "
            "padding: 0px 6px; font-size: 10px; font-weight: bold; border: none;"
        )
        self._flag_badge.hide()
        header.addWidget(self._flag_badge, 0, Qt.AlignmentFlag.AlignTop)
        vbox.addLayout(header)

        # Status: coloured dot plus the status word, so it never relies on colour alone
        status_row = QHBoxLayout()
        status_row.setSpacing(5)
        self._status_dot = QLabel("●")
        self._status_dot.setStyleSheet("font-size: 9px; color: #d1d5db; background: transparent;")
        status_row.addWidget(self._status_dot)
        self._status_lbl = QLabel("ok")
        self._status_lbl.setStyleSheet("font-size: 11px; color: #6b7280; background: transparent;")
        status_row.addWidget(self._status_lbl)
        status_row.addStretch()
        vbox.addLayout(status_row)

        # Action type badges row
        self._badges_row = QHBoxLayout()
        self._badges_row.setSpacing(4)
        self._badges_row.setContentsMargins(0, 2, 0, 2)
        vbox.addLayout(self._badges_row)

        vbox.addStretch()

    def update_state(self, ms: ModuleState) -> None:
        self._out_of_scope = ms.status == "out_of_scope"
        strip, accent, status_text = _STATUS_STYLE.get(
            ms.status, ("#d1d5db", "#6b7280", ms.status)
        )
        self._strip_colour = strip
        self._strip.setStyleSheet(
            f"background: {strip}; border-radius: 7px 7px 0 0; border: none;"
        )
        self._set_background("#eceff3" if self._out_of_scope else "white")
        self._name_lbl.setStyleSheet(
            "font-weight: 600; font-size: 13px; background: transparent; "
            f"color: {'#9ca3af' if self._out_of_scope else '#111827'};"
        )
        self._status_lbl.setText(status_text)
        self._status_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {accent}; background: transparent;"
        )
        self._status_dot.setStyleSheet(f"font-size: 9px; color: {strip}; background: transparent;")

        # Flag badge
        unacked = sum(1 for f in ms.flags if not f.acknowledged)
        if unacked:
            has_error = any(f.type == "error" and not f.acknowledged for f in ms.flags)
            badge_bg = "#ef4444" if has_error else "#f59e0b"
            self._flag_badge.setText(f"{unacked} flag{'s' if unacked > 1 else ''}")
            self._flag_badge.setStyleSheet(
                f"background: {badge_bg}; color: white; border-radius: 7px; "
                "padding: 2px 7px; font-size: 10px; font-weight: bold;"
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

    def enterEvent(self, event) -> None:
        self._apply_shadow(blur=22, offset=5, alpha=35)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._apply_shadow(blur=10, offset=2, alpha=18)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)
