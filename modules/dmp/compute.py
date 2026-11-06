"""
DMP — compute.py

Turns the questionnaire into the DMP's startup configuration: which learned grinding
primitive (pose + wrench files) belongs to which defect class, and the tool-to-defect
offset. The primitives are generated offline from demonstrations; COT never regenerates
them, so duration, basis count and phase samples are reported as read-only information.

Usage (called by compute_runner.py as a subprocess):
    python -m modules.dmp.compute <use_case_json_path> <output_dir>
"""

import json
import math
import os
import sys
from datetime import datetime

from app.engine.collection import active_items, collection_options
from app.engine.schema import DMP_CONFIG

_PRIMITIVES = next(q for q in DMP_CONFIG if q["id"] == "primitives")

# Explicit mapping from COT defect classes to the DMP's primitive classes (confirmed by IIT).
# The DMP has no learned primitive for "other", so that class blocks deployment.
_DEFECT_CLASS_LABELS = {"positive_dent": "POSITIVE", "negative_dent": "NEGATIVE"}

# Nominal replay time of each class's learned artifact (IIT spec, read-only).
_PRIMITIVE_DURATION_S = {"positive_dent": 17.717, "negative_dent": 17.818}
_RBF_BASIS_COUNT = 24
_PHASE_SAMPLES = 256

_PATH_FIELDS = (("pose_path", "pose path"), ("wrench_path", "wrench path"))
_AXES = ("x", "y", "z")

_PATHS_NOTE = "COT only checks that the paths are filled in, not that the files exist on the runtime"
_OFFSET_NOTE = "COT cannot verify the tool offset calibration"


def _drivers(answers: dict) -> dict:
    return {"q8_defects": answers.get("q8_defects") or []}


def _selected_primitives(answers: dict) -> dict:
    """Stored answers of the selected Positive/Negative Dent only: {class: {field: value}}."""
    return active_items(_PRIMITIVES, answers.get("primitives"), _drivers(answers))


def _path(item: dict, field: str) -> str:
    return str(item.get(field) or "").strip()


def _offset(answers: dict, axis: str):
    """(value, problem): the offset component in metres, or why it cannot be used."""
    raw_value = answers.get(f"tool_defect_offset_{axis}_m")
    raw = str(raw_value).strip() if raw_value is not None else ""
    if not raw:
        return None, "is missing"
    try:
        value = float(raw)
    except ValueError:
        return None, "is not a number"
    return (value, None) if math.isfinite(value) else (None, "is not a number")


def run(answers: dict) -> dict:
    """Flat str/int/float outputs; anything not configured (yet) is left out."""
    outputs: dict = {}
    selected = _selected_primitives(answers)

    outputs["primitive_classes"] = ",".join(_DEFECT_CLASS_LABELS[option] for option in selected)
    for option, item in selected.items():
        for field, _ in _PATH_FIELDS:
            path = _path(item, field)
            if path:
                outputs[f"primitive_{option}_{field}"] = path
        outputs[f"primitive_{option}_duration_s"] = _PRIMITIVE_DURATION_S[option]

    for axis in _AXES:
        value, _ = _offset(answers, axis)
        if value is not None:
            outputs[f"tool_defect_offset_{axis}_m"] = value

    outputs["orientation_mode"] = "fixed"
    outputs["rbf_basis_count"] = _RBF_BASIS_COUNT
    outputs["phase_samples"] = _PHASE_SAMPLES
    return outputs


def deploy_blockers(answers: dict) -> list:
    """Human-readable reasons this configuration must not be deployed yet."""
    blockers = []
    defects = answers.get("q8_defects") or []

    if not defects:
        blockers.append("no defect class selected (Q8)")
    if "other" in defects:
        description = str(answers.get("q8_other_defect") or "").strip() or "other"
        blockers.append(f"defect class '{description}' has no learned grinding primitive")

    labels = {o["value"]: o["label"] for o in collection_options(_PRIMITIVES)}
    for option, item in _selected_primitives(answers).items():
        for field, field_label in _PATH_FIELDS:
            if not _path(item, field):
                blockers.append(f"{labels[option]}: {field_label} is missing")

    for axis in _AXES:
        _, problem = _offset(answers, axis)
        if problem:
            blockers.append(f"tool defect offset {axis} (m) {problem}")
    return blockers


def notes(answers: dict) -> list:
    """Things to know before deploying that do not block it."""
    return [_PATHS_NOTE, _OFFSET_NOTE]


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python -m modules.dmp.compute <use_case_json> <output_dir>", file=sys.stderr)
        sys.exit(1)

    use_case_path = sys.argv[1]
    output_dir = sys.argv[2]

    with open(use_case_path, encoding="utf-8") as f:
        use_case = json.load(f)

    answers = use_case.get("answers", {})
    answers = {**answers, **use_case.get("module_answers", {}).get("dmp", {})}

    print(f"[dmp] Computing configuration for use case: {use_case.get('name', '?')}")
    outputs = run(answers)
    blockers = deploy_blockers(answers)

    result = {
        "module_id": "dmp",
        "success": True,
        "outputs": outputs,
        "error": None,
        "computed_at": datetime.utcnow().isoformat(),
        "deploy_blockers": blockers,
        "notes": notes(answers),
    }

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"[dmp] Result written to {out_path}")
    print(f"[dmp] Deploy blockers: {blockers or 'none'}")
    for k, v in outputs.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
