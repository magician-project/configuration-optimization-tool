from typing import Dict, Any, List
from app.models.questionnaire import QuestionnaireAnswers
from app.models.use_case import ModuleImpact, Flag, ModuleState, ConfidenceScore, UseCase
from app.engine.module_registry import MODULES


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
    # Q2 extensions: Grabber camera hardware parameters
    # ------------------------------------------------------------------
    cam_res = answers.q2_camera_resolution or {}
    if cam_res.get("width") or cam_res.get("height"):
        w = cam_res.get("width", "?")
        h = cam_res.get("height", "?")
        result["grabber"]["impacts"].append(_impact(
            characteristic="Camera resolution",
            affects="Input",
            what_changes=(
                f"Capture resolution set to {w}×{h} px. "
                "Update --size flag and params.yaml width/height accordingly. "
                "Higher resolutions increase storage and processing load."
            ),
            action_type="reconfigure",
            reason="Q2: Camera resolution specified",
        ))
        total_characteristics += 1

    if answers.q2_camera_framerate:
        fps = float(answers.q2_camera_framerate)
        ram_note = " RAM-backed storage (--ram) is required at this frame rate." if fps > 10 else ""
        result["grabber"]["impacts"].append(_impact(
            characteristic="Camera frame rate",
            affects="Input",
            what_changes=(
                f"Target frame rate: {fps} Hz.{ram_note} "
                "Update --fps flag and params.yaml frame_rate."
            ),
            action_type="reconfigure",
            reason="Q2: Camera frame rate specified",
        ))
        if fps > 10:
            result["grabber"]["flags"].append(_flag(
                id="flag_framerate_ram",
                type="warning",
                message=(
                    f"Frame rate {fps} Hz > 10 Hz requires RAM-backed storage. "
                    "Ensure --ram flag is set in launch args."
                ),
                module_id="grabber",
            ))
        total_characteristics += 1

    if answers.q2_stream_shm == "yes":
        stream_name = answers.q2_stream_shm_name or "stream1"
        result["grabber"]["impacts"].append(_impact(
            characteristic="Shared memory streaming",
            affects="Output",
            what_changes=(
                f"Camera frames will be published to POSIX shared memory stream '{stream_name}' "
                "(--stream flag). File output is disabled when streaming. "
                "Required for the live vision classifier."
            ),
            action_type="reconfigure",
            reason="Q2: Shared memory streaming enabled",
        ))
        total_characteristics += 1

    # ------------------------------------------------------------------
    # Q3 extensions: Grabber hardware paths and lighting mode
    # ------------------------------------------------------------------
    if "distance" in answers.q3_additional_sensors:
        lighting = answers.q3_lighting_mode or "none"
        lighting_label = {
            "rlight": "round-robin", "dlight": "distance-based",
            "tlight": "pattern-based", "trigger": "manual trigger", "none": "none",
        }.get(lighting, lighting)
        result["grabber"]["impacts"].append(_impact(
            characteristic="Distance sensor + lighting controller (Arduino)",
            affects="Process",
            what_changes=(
                f"Arduino distance sensor thread enabled. "
                f"Lighting mode: {lighting_label}. "
                f"Serial port: {answers.q3_arduino_path or '/dev/ttyUSB0'}. "
                "Update --arduino and --distance flags in launch args."
            ),
            action_type="reconfigure",
            reason="Q3: Distance sensors selected",
        ))
        total_characteristics += 1

    if "tactile" in answers.q3_additional_sensors and answers.q3_force_sensor_ip:
        result["grabber"]["impacts"].append(_impact(
            characteristic="ATI NetFT force/torque sensor",
            affects="Input",
            what_changes=(
                f"ATI NetFT configured at {answers.q3_force_sensor_ip}:"
                f"{answers.q3_force_sensor_port or 49152}. "
                "Update ati_ip and ati_port in params.yaml."
            ),
            action_type="reconfigure",
            reason="Q3: Force sensor IP configured",
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
    # Q8 extensions: Vision Classifier configuration
    # ------------------------------------------------------------------
    clf_model = answers.q_clf_model
    clf_tile  = answers.q_clf_tile_size
    clf_path  = (answers.q_clf_model_path or "").strip()
    clf_data  = (answers.q_clf_dataset_dir or "").strip()

    if clf_model:
        result["vision_classifier"]["impacts"].append(_impact(
            characteristic="Classifier backbone architecture",
            affects="Process",
            what_changes=(
                f"Backbone set to '{clf_model}'. "
                "This must match the backbone used during training. "
                "Update model field in training_config.json and live_config.json."
            ),
            action_type="reconfigure",
            reason="Q8 ext: Classifier backbone selected",
        ))
        total_characteristics += 1

    if clf_tile:
        result["vision_classifier"]["impacts"].append(_impact(
            characteristic="Tile size",
            affects="Input, Process",
            what_changes=(
                f"Tile size set to {clf_tile} px. "
                "Tile size must match between training and live inference. "
                "Update tile_size in training_config.json and step_size in live_config.json accordingly."
            ),
            action_type="reconfigure",
            reason="Q8 ext: Tile size specified",
        ))
        total_characteristics += 1

    if clf_path:
        import os as _os
        exists = _os.path.isfile(clf_path)
        result["vision_classifier"]["impacts"].append(_impact(
            characteristic="Pre-trained model checkpoint",
            affects="Input",
            what_changes=(
                f"Model checkpoint: {clf_path}. "
                + ("File found — training will be skipped." if exists
                   else "WARNING: file not found at this path.")
            ),
            action_type="reconfigure",
            reason="Q8 ext: Model path provided",
        ))
        if not exists:
            result["vision_classifier"]["flags"].append(_flag(
                id="flag_model_not_found",
                type="error",
                message=f"Model checkpoint not found: {clf_path}. Verify the path before deploying.",
                module_id="vision_classifier",
            ))
        total_characteristics += 1
    elif clf_data:
        result["vision_classifier"]["impacts"].append(_impact(
            characteristic="Training dataset",
            affects="Input",
            what_changes=(
                f"Dataset directory: {clf_data}. "
                "No pre-trained model provided — retraining is required. "
                "Run trainMagicianVisionClassifierTorch.py with the generated training_config.json."
            ),
            action_type="retrain",
            reason="Q8 ext: Dataset directory provided, no model path",
        ))
        result["vision_classifier"]["flags"].append(_flag(
            id="flag_retrain_required",
            type="warning",
            message=(
                "Retraining required before deployment. "
                "Use the generated training_config.json with trainMagicianVisionClassifierTorch.py."
            ),
            module_id="vision_classifier",
        ))
        total_characteristics += 1

    if answers.q_clf_use_lasers == "yes":
        result["vision_classifier"]["impacts"].append(_impact(
            characteristic="Laser distance sensor fusion",
            affects="Input, Output",
            what_changes=(
                "Classifier will subscribe to 3 distance sensor topics and fuse depth into "
                "DetectionM messages using IDW interpolation. "
                "Laser topics and pixel positions must be set in live_config.json."
            ),
            action_type="reconfigure",
            reason="Q8 ext: Laser fusion enabled",
        ))
        total_characteristics += 1

    # Advanced polarization channels
    extra_channels = [
        c for c, field in [("AoLP", answers.q_clf_aolp), ("DoLP", answers.q_clf_dolp),
                           ("Unpolarized", answers.q_clf_unpolarized)]
        if field == "yes"
    ]
    if extra_channels:
        result["vision_classifier"]["impacts"].append(_impact(
            characteristic="Extra polarization input channels",
            affects="Process",
            what_changes=(
                f"Additional input channels enabled: {', '.join(extra_channels)}. "
                "These are computed from the 4 Stokes base channels. "
                "Must be set in training_config.json (hparams) and the model must be trained with them."
            ),
            action_type="reconfigure",
            reason="Q8 ext: Polarization channels configured",
        ))
        result["vision_classifier"]["flags"].append(_flag(
            id="flag_polar_channels",
            type="warning",
            message=(
                f"Extra polarization channels ({', '.join(extra_channels)}) are baked into the model "
                "at training time. Ensure any existing checkpoint was also trained with these settings."
            ),
            module_id="vision_classifier",
        ))
        total_characteristics += 1

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

    # Cat 1: Robot Arms
    if answers.q1_robot_arms:
        score += 1

    # Cat 2: Camera / Sensors (original + new grabber camera questions)
    if (answers.q2_camera_type or answers.q3_additional_sensors
            or answers.q2_camera_resolution or answers.q2_camera_framerate
            or answers.q2_camera_exposure or answers.q2_stream_shm):
        score += 1

    # Cat 3: Lighting
    if answers.q4_lighting:
        score += 1

    # Cat 4: Material / Size
    if answers.q5_materials or answers.q6_object_size:
        score += 1

    # Cat 5: Defect Types (original + classifier config)
    if answers.q8_defects or answers.q_clf_model or answers.q_clf_tile_size or answers.q_clf_threshold:
        score += 1

    # Cat 6: Time / Profit
    if answers.q9_time or answers.q10_profit:
        score += 1

    # Cat 7: Mesh
    if answers.q7_mesh:
        score += 1

    # Cat 8: Grabber Hardware (force sensor, lighting mode, serial paths)
    if (answers.q3_force_sensor_ip or answers.q3_lighting_mode
            or answers.q3_arduino_path or answers.q3_teensy_path
            or answers.q2_camera_framerate):
        score += 1

    # Cat 9: Classifier Config (model path or dataset + key inference params)
    if (answers.q_clf_model_path or answers.q_clf_dataset_dir
            or answers.q_clf_use_lasers or answers.q_clf_threshold or answers.q_clf_fps):
        score += 1

    pct = (score / 9) * 100
    if pct < 40:
        level = "low"
    elif pct < 70:
        level = "medium"
    else:
        level = "high"

    return {"score": score, "max": 9, "percentage": round(pct, 1), "level": level}


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
