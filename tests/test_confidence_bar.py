"""
ConfidenceBar must show one dot per scoring category, so the dots always match "score / max"
(grinding-only scores out of 5, other pipelines out of 9).
"""

import pytest
from PySide6.QtWidgets import QApplication

from app.models.use_case import ConfidenceScore
from gui.components.confidence_bar import ConfidenceBar


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.mark.parametrize("max_score", [5, 9])
def test_dot_count_follows_confidence_max(qapp, max_score):
    bar = ConfidenceBar()

    bar.update_score(ConfidenceScore(score=2, max=max_score, percentage=100 * 2 / max_score, level="low"))

    assert len(bar._dots) == max_score
