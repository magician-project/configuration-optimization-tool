"""Conservative estimate of one grinding cycle per defect, from the IIT baseline and the Cartesian Controller answers."""

from __future__ import annotations

import math
from typing import Optional, Sequence

from app.engine.module_config import number_values
from app.engine.schema import CARTESIAN_CONTROLLER_CONFIG

# Nominal replay time of each defect class's learned primitive (IIT spec, COT_DMP).
BASELINE_PRIMITIVE_DURATION_S = {"positive_dent": 17.717, "negative_dent": 17.818}

BASELINE_NOTE = "IIT baseline, not measured from configured primitive files"

_SECONDS_PER_UNIT = {"seconds": 1.0, "minutes": 60.0, "hours": 3600.0}

# The Cartesian Controller phases that make up one cycle, besides the primitive replay.
_CYCLE_PARAMETERS = ("reach_duration_s", "touch_dwell_s", "unload_extra_duration_s", "go_away_duration_s")


def baseline_cycle_time_s(defect_classes: Sequence[str], cartesian_answers: dict) -> Optional[float]:
    """Seconds for one defect: reach + touch dwell + longest selected primitive + extra unload + go away.

    Unanswered Cartesian Controller parameters take their defaults. None when no selected class has a
    baseline duration, or when a stored answer is not a finite, non-negative number.
    """
    durations = [BASELINE_PRIMITIVE_DURATION_S[c] for c in defect_classes if c in BASELINE_PRIMITIVE_DURATION_S]
    if not durations:
        return None
    try:
        values = number_values(CARTESIAN_CONTROLLER_CONFIG, cartesian_answers)
    except (TypeError, ValueError):
        return None
    phases = [values[key] for key in _CYCLE_PARAMETERS]
    if not all(math.isfinite(p) and p >= 0 for p in phases):
        return None
    return sum(phases) + max(durations)


def time_budget_s(time_constraint: Optional[str], value: Optional[float], unit: Optional[str]) -> Optional[float]:
    """The Q9 time budget in seconds, or None when there is no (usable) budget."""
    if time_constraint != "tight" or value is None or not math.isfinite(value) or value <= 0:
        return None
    seconds_per_unit = _SECONDS_PER_UNIT.get(unit or "minutes")
    return value * seconds_per_unit if seconds_per_unit else None
