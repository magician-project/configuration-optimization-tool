"""
ConfidenceBar — segmented dot display showing questionnaire completeness (score / max).
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel

from app.models.use_case import ConfidenceScore

_COLOURS = {
    "high":   ("#16a34a", "#dcfce7", "Comprehensive configuration provided."),
    "medium": ("#d97706", "#fef3c7", "Good start — fill remaining fields for better recommendations."),
    "low":    ("#dc2626", "#fee2e2", "Answer more questions to improve recommendation quality."),
}

_DEFAULT_DOT_COUNT = 7


class ConfidenceBar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._dots: list[QLabel] = []
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(
            "background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 2px;"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(6)

        # Top row: score label + level badge
        top = QHBoxLayout()
        self._score_label = QLabel("Confidence  0 / 7")
        self._score_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #111827;")
        top.addWidget(self._score_label)
        top.addStretch()
        self._level_badge = QLabel("LOW")
        self._level_badge.setStyleSheet(
            "background: #fee2e2; color: #dc2626; border-radius: 4px; "
            "padding: 2px 10px; font-size: 11px; font-weight: bold;"
        )
        top.addWidget(self._level_badge)
        root.addLayout(top)

        # Segmented dots row (one dot per scoring category, so the count follows the score's max)
        self._dots_row = QHBoxLayout()
        self._dots_row.setSpacing(6)
        self._set_dot_count(_DEFAULT_DOT_COUNT)
        root.addLayout(self._dots_row)

        self._hint_label = QLabel("Answer questions to improve recommendation quality.")
        self._hint_label.setStyleSheet("color: #9ca3af; font-size: 11px;")
        root.addWidget(self._hint_label)

    def _set_dot_count(self, count: int) -> None:
        while self._dots_row.count():
            item = self._dots_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._dots = []
        for _ in range(count):
            dot = QLabel()
            dot.setFixedSize(32, 10)
            dot.setStyleSheet("background: #e5e7eb; border-radius: 5px;")
            self._dots.append(dot)
            self._dots_row.addWidget(dot)
        self._dots_row.addStretch()

    def update_score(self, confidence: ConfidenceScore) -> None:
        if len(self._dots) != confidence.max:
            self._set_dot_count(confidence.max)
        fg, bg, hint = _COLOURS.get(confidence.level, ("#6b7280", "#f3f4f6", ""))

        self._score_label.setText(
            f"Confidence  {confidence.score} / {confidence.max}  ({confidence.percentage:.0f}%)"
        )
        self._level_badge.setText(confidence.level.upper())
        self._level_badge.setStyleSheet(
            f"background: {bg}; color: {fg}; border-radius: 4px; "
            "padding: 2px 10px; font-size: 11px; font-weight: bold;"
        )
        self._hint_label.setText(hint)
        self._hint_label.setStyleSheet(f"color: {fg}; font-size: 11px;")

        for i, dot in enumerate(self._dots):
            filled = i < confidence.score
            dot.setStyleSheet(
                f"background: {fg}; border-radius: 5px;"
                if filled else
                "background: #e5e7eb; border-radius: 5px;"
            )
