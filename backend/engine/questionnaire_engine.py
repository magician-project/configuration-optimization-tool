from typing import Dict, Any, List
from models.questionnaire import QuestionnaireAnswers
from models.use_case import ModuleImpact, Flag, ModuleState, ConfidenceScore, UseCase
from engine.module_registry import MODULES


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_impacts(answers: QuestionnaireAnswers) -> Dict[str, Any]:
    """
    Pure function. Given questionnaire answers, returns:
      {
        "module_impacts": {module_id: {"impacts": [...], "flags": [...]}},
        "confidence": {score, max, percentage, level},
      }
    """
    result: Dict[str, Dict] = {mid: {"impacts": [], "flags": []} for mid in MODULES}
    total_characteristics = 0

    # ------------------------------------------------------------------
    # Q1: Number of robot arms
    # ------------------------------------------------------------------
    if answers.q1_robot_arms == "multiple":
        result["grabber"]["impacts"].append(_impact(
            characteristic="Multiple robot arms",
            affects="Process",
            what_changes=(
                "The Grabber must execute multi-threaded peripheral management to handle "
                "parallel sensor data streams from multiple robot arms simultaneously. "
                "The existing threading architecture must be extended to support concurrent "
                "operations for each arm."
            ),
            action_type="reconfigure",
            reason="Q1: Multiple robot arms selected",
        ))
        result["orienteering_solver"]["impacts"].append(_impact(
            characteristic="Multiple robot arms",
            affects="Problem Description",
            what_changes=(
                "Scheduling problem changes from Orienteering Problem (OP) to "
                "Team Orienteering Problem (TOP). Multiple agents must cooperatively share "
                "and schedule defect remediation tasks. Algorithm and Hyperparameters "
                "processes must be reconfigured for multi-agent scheduling."
            ),
            action_type="reconfigure",
            reason="Q1: Multiple robot arms selected",
        ))
        result["orienteering_solver"]["flags"].append(_flag(
            id="flag_multi_arm",
            type="human_oversight",
            message=(
                "Team Orienteering Problem formulation and arm synchronisation must be "
                "reviewed by a robotics engineer."
            ),
            module_id="orienteering_solver",
        ))
        total_characteristics += 2

    # ------------------------------------------------------------------
    # Q2: Camera type
    # ------------------------------------------------------------------
    if answers.q2_camera_type in ("gige", "other"):
        spec = f" ({answers.q2_camera_spec})" if answers.q2_camera_spec else ""
        result["grabber"]["impacts"].append(_impact(
            characteristic="Usage of a different GiGE camera",
            affects="Input",
            what_changes=(
                f"Camera{spec} selected. ARAVIS SDK is compatible with all GigE Vision cameras "
                "so no software change is required for standard GiGE swaps. For non-standard "
                "types (thermal, hyperspectral) additional investigation may be needed outside "
                "this characteristic."
            ),
            action_type="review",
            reason="Q2: Non-default camera type selected",
        ))
        total_characteristics += 1

    # ------------------------------------------------------------------
    # Q3: Additional sensor modalities
    # ------------------------------------------------------------------
    if answers.q3_additional_sensors:
        sensor_labels = {
            "tactile": "Tactile/Force sensing",
            "vision": "Additional vision sensors",
        }
        sensors_text = ", ".join(
            sensor_labels.get(s, s) for s in answers.q3_additional_sensors
        )
        result["grabber"]["impacts"].append(_impact(
            characteristic="Addition of an extra sensor modality",
            affects="Process",
            what_changes=(
                f"Grabber processing architecture must be extended for: {sensors_text}. "
                "Either route new sensor data through existing microcontrollers "
                "(Arduino_Thread / Teensy_Thread) or add a new driver thread. "
                "Tactile_Features_Calculator may also need updating."
            ),
            action_type="reconfigure",
            reason="Q3: Additional sensor modalities selected",
        ))
        total_characteristics += 1

    # ------------------------------------------------------------------
    # Q4: Lighting
    # ------------------------------------------------------------------
    if answers.q4_lighting == "additional":
        result["grabber"]["impacts"].append(_impact(
            characteristic="Addition of more lights for better illumination",
            affects="Process",
            what_changes=(
                "Extra LED units can be connected to spare channels on the existing "
                "Camera Light Controller. Minor update to Arduino_Thread process to "
                "activate additional channels. Camera exposure must be recalibrated "
                "for the new lighting conditions."
            ),
            action_type="reconfigure",
            reason="Q4: Additional lighting required",
        ))
        total_characteristics += 1

    # ------------------------------------------------------------------
    # Q5: Surface materials
    # ------------------------------------------------------------------
    if answers.q5_materials:
        mat_list = list(answers.q5_materials)
        if "other" in mat_list and answers.q5_other_material:
            mat_list = [m for m in mat_list if m != "other"] + [answers.q5_other_material]
        elif "other" in mat_list:
            mat_list = [m for m in mat_list if m != "other"] + ["(other — unspecified)"]
        mat_text = ", ".join(mat_list)

        result["orienteering_solver"]["impacts"].append(_impact(
            characteristic="Material",
            affects="DefectProfitCalculator, Defect Information",
            what_changes=(
                f"Material(s): {mat_text}. Profit model and service time lookup must be "
                "calibrated for these materials. Partners must supply material-specific "
                "profit and service time specifications."
            ),
            action_type="reconfigure",
            reason="Q5: Material(s) selected",
        ))
        result["localiser"]["impacts"].append(_impact(
            characteristic="Material Y",
            affects="Process",
            what_changes=(
                f"Localization approach must be selected based on material: {mat_text}. "
                "Approach 1 (model-free, no mesh), Approach 2 or 3 (model-based, requires mesh). "
                "Selection depends on mesh availability (Q7)."
            ),
            action_type="reconfigure",
            reason="Q5: Material(s) selected",
        ))
        result["tactile_sensor"]["impacts"].append(_impact(
            characteristic="Different materials, object sizes, dirt/dent types, and time constraints",
            affects="Input",
            what_changes=(
                f"Tactile Classifier ML model must be retrained on labeled data for: {mat_text}. "
                "Retraining pipeline: Pre_calculations → Neural_network (CNN-LSTM) → Ensemble. "
                "Collect new material-specific tactile data before retraining."
            ),
            action_type="retrain",
            reason="Q5: New material(s) selected",
        ))
        result["vision_classifier"]["impacts"].append(_impact(
            characteristic="(implicit) Retrain vision model on new material data",
            affects="Input",
            what_changes=(
                f"Vision Classifier model must be retrained on images of: {mat_text}. "
                "Update Vision Model Name parameter in the Configuration Module after retraining."
            ),
            action_type="retrain",
            reason="Q5: New material(s) selected — vision retraining required",
        ))
        result["tactile_sensor"]["flags"].append(_flag(
            id="flag_retrain",
            type="error",
            message=(
                "New material selected — vision and tactile classifiers must be retrained "
                "on data covering this material."
            ),
            module_id="tactile_sensor",
        ))
        result["vision_classifier"]["flags"].append(_flag(
            id="flag_retrain_vision",
            type="error",
            message=(
                "New material selected — vision classifier must be retrained "
                "on data covering this material."
            ),
            module_id="vision_classifier",
        ))
        total_characteristics += 4

    # ------------------------------------------------------------------
    # Q6: Object sizes
    # ------------------------------------------------------------------
    if answers.q6_object_size:
        size_label = {
            "small": "small objects",
            "large": "large objects (e.g., boats, vehicles)",
            "variable": "variable sizes",
        }.get(answers.q6_object_size, answers.q6_object_size)
        dims_text = ""
        if answers.q6_dimensions:
            d = answers.q6_dimensions
            dims_text = (
                f" (approx. {d.length}×{d.width}×{d.height} {d.unit})"
                if all([d.length, d.width, d.height])
                else ""
            )
        result["tactile_sensor"]["impacts"].append(_impact(
            characteristic="Different materials, object sizes, dirt/dent types, and time constraints",
            affects="Input",
            what_changes=(
                f"Object size: {size_label}{dims_text}. Size affects how training data is "
                "collected and how the tactile model is trained. Data collection protocols "
                "must reflect the contact dynamics appropriate for this size."
            ),
            action_type="review",
            reason="Q6: Object size specified",
        ))
        total_characteristics += 1

    # ------------------------------------------------------------------
    # Q7: 3D mesh availability
    # ------------------------------------------------------------------
    if answers.q7_mesh == "available":
        result["localiser"]["impacts"].append(_impact(
            characteristic="Material Y",
            affects="Process",
            what_changes=(
                "Mesh is available. Localiser can use model-based localization (Approach 2 or 3). "
                "Provide the mesh file (.off / .stl / .obj) as input parameter to the Localiser."
            ),
            action_type="reconfigure",
            reason="Q7: Mesh available",
        ))
        total_characteristics += 1
    elif answers.q7_mesh == "in_preparation":
        status_label = {
            "cad": "CAD model exists — mesh can be derived",
            "scanning": "Needs 3D scanning",
            "unknown": "Status unknown",
        }.get(answers.q7_mesh_status or "", "")
        result["localiser"]["impacts"].append(_impact(
            characteristic="Material Y",
            affects="Process",
            what_changes=(
                f"Mesh in preparation ({status_label}). Configuration is provisional — "
                "use model-free Approach 1 as placeholder. Revisit and switch to "
                "model-based approach once mesh is finalized."
            ),
            action_type="review",
            reason="Q7: Mesh in preparation",
        ))
        result["localiser"]["flags"].append(_flag(
            id="flag_mesh_prep",
            type="warning",
            message=(
                "Localisation module configuration is provisional until the mesh is available. "
                "Revisit this assessment when the mesh is ready."
            ),
            module_id="localiser",
        ))
        total_characteristics += 1
    elif answers.q7_mesh == "not_available":
        result["localiser"]["impacts"].append(_impact(
            characteristic="Material Y",
            affects="Process",
            what_changes=(
                "No mesh available. Only model-free localization (Approach 1) can be used. "
                "Initiate 3D scanning or CAD model retrieval immediately — "
                "this is a blocking prerequisite for model-based localization."
            ),
            action_type="review",
            reason="Q7: Mesh not available",
        ))
        result["localiser"]["flags"].append(_flag(
            id="flag_mesh_missing",
            type="error",
            message=(
                "Localisation approach cannot be finalised without a mesh. "
                "Initiate 3D scanning or CAD retrieval before proceeding."
            ),
            module_id="localiser",
        ))
        total_characteristics += 1

    # ------------------------------------------------------------------
    # Q8: Defect types
    # ------------------------------------------------------------------
    if answers.q8_defects:
        defect_labels = {
            "dents": "Dents/Deformations",
            "dirt": "Dirt/Contamination",
            "surface_damage": "Surface damage",
        }
        defects_text = ", ".join(
            defect_labels.get(d, d) for d in answers.q8_defects
        )
        result["orienteering_solver"]["impacts"].append(_impact(
            characteristic="Type defect",
            affects="DefectProfitCalculator, Defect Information",
            what_changes=(
                f"Defect types: {defects_text}. Profit function and service time model must be "
                "calibrated per defect type. Partners must supply defect-type-specific "
                "economic and operational parameters."
            ),
            action_type="reconfigure",
            reason="Q8: Defect types selected",
        ))
        result["tactile_sensor"]["impacts"].append(_impact(
            characteristic="Different materials, object sizes, dirt/dent types, and time constraints",
            affects="Input",
            what_changes=(
                f"Tactile Classifier must have training data for defect types: {defects_text}. "
                "Classes in the CNN-LSTM output layer must match the selected types. "
                "Re-label and retrain if any type is new."
            ),
            action_type="retrain",
            reason="Q8: Defect types selected",
        ))
        total_characteristics += 2

        geometric = {"dents", "surface_damage"}
        if any(d in geometric for d in answers.q8_defects):
            result["tactile_sensor"]["flags"].append(_flag(
                id="flag_geometric_defects",
                type="warning",
                message=(
                    "Dents and surface damage require 3D or depth-aware data. "
                    "Verify labelled examples exist before training."
                ),
                module_id="tactile_sensor",
            ))

    # ------------------------------------------------------------------
    # Q9: Time constraints
    # ------------------------------------------------------------------
    if answers.q9_time == "none":
        result["orienteering_solver"]["impacts"].append(_impact(
            characteristic="No time constraint",
            affects="Problem Description",
            what_changes=(
                "No time budget — problem reformulates from Orienteering Problem (OP) to "
                "Travelling Salesman Problem (TSP): all defects visited in optimal sequence. "
                "Algorithm process must switch to a TSP solver; time_restriction input is ignored."
            ),
            action_type="reconfigure",
            reason="Q9: No time constraints",
        ))
        result["localiser"]["impacts"].append(_impact(
            characteristic="No time constraint",
            affects="Process",
            what_changes=(
                "Localiser can run more exhaustive search and refinement cycles. "
                "Time deadline check within the Localiser can be removed or relaxed, "
                "potentially improving localization accuracy."
            ),
            action_type="reconfigure",
            reason="Q9: No time constraints",
        ))
        total_characteristics += 2
    elif answers.q9_time == "tight":
        time_str = ""
        if answers.q9_time_value is not None:
            time_str = f" ({answers.q9_time_value} {answers.q9_time_unit or 'minutes'})"
        result["orienteering_solver"]["impacts"].append(_impact(
            characteristic="Addition of defects have to happen in a certain timeframe",
            affects="Problem Description",
            what_changes=(
                f"Tight time budget{time_str}. Problem changes from OP to "
                "Orienteering Problem with Time Windows (OPTW). Time windows must be "
                "encoded in Problem_description. Algorithm and max_compute_time must be "
                "updated for a solver that handles time window constraints."
            ),
            action_type="reconfigure",
            reason="Q9: Tight time constraints specified",
        ))
        total_characteristics += 1

    # ------------------------------------------------------------------
    # Q10: Profit / priority definition
    # ------------------------------------------------------------------
    if answers.q10_profit == "custom":
        result["orienteering_solver"]["impacts"].append(_impact(
            characteristic="Profit definition changes",
            affects="Problem Description, DefectProfitCalculator",
            what_changes=(
                "Custom profit/priority criteria. Default profit model replaced with a "
                "domain-specific function — may change OP variant to OPVP (Variable Profits). "
                "DefectProfitCalculator internal logic must be rewritten. "
                "Partners must supply the new profit function specification."
            ),
            action_type="reconfigure",
            reason="Q10: Custom profit/priority criteria",
        ))
        result["orienteering_solver"]["flags"].append(_flag(
            id="flag_custom_profit",
            type="human_oversight",
            message=(
                "Custom profit criteria cannot be verified automatically. "
                "A domain expert must sign off before deployment."
            ),
            module_id="orienteering_solver",
        ))
        total_characteristics += 1

    # ------------------------------------------------------------------
    # Cross-cutting flag: >= 5 characteristics triggered
    # ------------------------------------------------------------------
    affected_modules = [mid for mid, data in result.items() if data["impacts"]]
    if total_characteristics >= 5:
        n = len(affected_modules)
        for mid in affected_modules:
            result[mid]["flags"].append(_flag(
                id="flag_cross_cutting",
                type="warning",
                message=(
                    f"Changes span {n} module(s). Phased integration and "
                    "cross-module testing is strongly recommended."
                ),
                module_id=mid,
            ))

    confidence = _compute_confidence(answers)
    return {"module_impacts": result, "confidence": confidence}


def apply_impacts_to_modules(use_case: UseCase, result: Dict[str, Any]) -> None:
    """
    Mutates use_case.modules in-place with fresh impacts and flags.
    Preserves flag acknowledged state where flag IDs match.
    Resets module status to 'ok' or 'needs_action' based on new impacts.
    """
    module_impacts = result["module_impacts"]
    use_case.confidence = ConfidenceScore(**result["confidence"])

    for mid, info in MODULES.items():
        data = module_impacts[mid]
        current: ModuleState = use_case.modules.get(mid)

        # Preserve acknowledged state from previous flags
        prev_acked: Dict[str, bool] = {}
        if current:
            for f in current.flags:
                prev_acked[f.id] = f.acknowledged

        new_impacts = [ModuleImpact(**i) for i in data["impacts"]]
        new_flags: List[Flag] = []
        seen_flag_ids: set = set()
        for f in data["flags"]:
            if f["id"] not in seen_flag_ids:
                seen_flag_ids.add(f["id"])
                flag = Flag(**f)
                flag.acknowledged = prev_acked.get(flag.id, False)
                new_flags.append(flag)

        new_status = "needs_action" if new_impacts else "ok"

        use_case.modules[mid] = ModuleState(
            module_id=mid,
            module_name=info["name"],
            description=info["description"],
            status=new_status,
            impacts=new_impacts,
            flags=new_flags,
        )


# ---------------------------------------------------------------------------
# Confidence scoring (7 categories)
# ---------------------------------------------------------------------------

def _compute_confidence(answers: QuestionnaireAnswers) -> Dict[str, Any]:
    score = 0

    # Category 1: Robot Arms
    if answers.q1_robot_arms:
        score += 1
    # Category 2: Camera / Sensors
    if answers.q2_camera_type or answers.q3_additional_sensors:
        score += 1
    # Category 3: Lighting
    if answers.q4_lighting:
        score += 1
    # Category 4: Material / Object Size
    if answers.q5_materials or answers.q6_object_size:
        score += 1
    # Category 5: Defect Types
    if answers.q8_defects:
        score += 1
    # Category 6: Time / Profit
    if answers.q9_time or answers.q10_profit:
        score += 1
    # Category 7: Mesh
    if answers.q7_mesh:
        score += 1

    pct = (score / 7) * 100
    if pct < 40:
        level = "low"
    elif pct < 70:
        level = "medium"
    else:
        level = "high"

    return {"score": score, "max": 7, "percentage": round(pct, 1), "level": level}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _impact(
    characteristic: str,
    affects: str,
    what_changes: str,
    action_type: str,
    reason: str,
) -> dict:
    return {
        "characteristic": characteristic,
        "affects": affects,
        "what_changes": what_changes,
        "action_type": action_type,
        "reason": reason,
    }


def _flag(id: str, type: str, message: str, module_id: str) -> dict:
    return {
        "id": id,
        "type": type,
        "message": message,
        "module_id": module_id,
        "acknowledged": False,
    }
