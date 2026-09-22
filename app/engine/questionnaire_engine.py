from typing import Dict, Any, List
from app.models.questionnaire import QuestionnaireAnswers
from app.models.use_case import ModuleImpact, Flag, ModuleState, ConfidenceScore, UseCase
from app.engine.module_registry import MODULES


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_impacts(answers: QuestionnaireAnswers, module_answers: dict = None) -> Dict[str, Any]:
    """
    Pure function. Given questionnaire answers and optional per-module config,
    returns:
      {
        "module_impacts": {module_id: {"impacts": [...], "flags": [...]}},
        "confidence": {score, max, percentage, level},
      }
    module_answers: dict keyed by module_id, e.g.
      {"vision_classifier": {"q_clf_model": "resnet18", ...}}
    """
    if module_answers is None:
        module_answers = {}
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
        grab = module_answers.get("grabber", {})
        lighting = grab.get("q_grab_lighting_mode") or "none"
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
                f"Serial port: {grab.get('q_grab_arduino_path') or '/dev/ttyUSB0'}. "
                "Update --arduino and --distance flags in launch args."
            ),
            action_type="reconfigure",
            reason="Q3: Distance sensors selected",
        ))
        total_characteristics += 1

    if "tactile" in answers.q3_additional_sensors:
        grab = module_answers.get("grabber", {})
        if grab.get("q_grab_force_sensor_ip"):
            result["grabber"]["impacts"].append(_impact(
                characteristic="ATI NetFT force/torque sensor",
                affects="Input",
                what_changes=(
                    f"ATI NetFT configured at {grab['q_grab_force_sensor_ip']}:"
                    f"{grab.get('q_grab_force_sensor_port') or 49152}. "
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
                f"Surface material(s): {mat_text}. If a new Setup still needs registering for this "
                "workpiece, mesh availability (Q7) determines whether Registration can proceed."
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
                "Mesh is available. If this workpiece's Setup still needs registering, provide the "
                "mesh file (.stl) as `q_local_mesh_path` so Registration (CAD/TCP point pairs) can proceed."
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
                f"Mesh in preparation ({status_label}). If this Setup isn't registered yet, Registration "
                "is blocked until the mesh is finalized; an already-registered Setup is unaffected."
            ),
            action_type="review",
            reason="Q7: Mesh in preparation",
        ))
        result["localiser"]["flags"].append(_flag(
            id="flag_mesh_prep",
            type="warning",
            message=(
                "Registering a new Localiser Setup is blocked until the mesh is available. "
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
                "No mesh available. Registering a new Localiser Setup cannot proceed — "
                "initiate 3D scanning or CAD model retrieval. An already-registered Setup is unaffected."
            ),
            action_type="review",
            reason="Q7: Mesh not available",
        ))
        result["localiser"]["flags"].append(_flag(
            id="flag_mesh_missing",
            type="error",
            message=(
                "A new Localiser Setup cannot be registered without a mesh. "
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
    # (fields now live in module_answers["vision_classifier"])
    # ------------------------------------------------------------------
    clf = module_answers.get("vision_classifier", {})
    clf_model = clf.get("q_clf_model")
    clf_tile = clf.get("q_clf_tile_size")
    clf_path = (clf.get("q_clf_model_path") or "").strip()
    clf_data = (clf.get("q_clf_dataset_dir") or "").strip()

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

    if clf.get("q_clf_use_lasers") == "yes":
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
        c for c, field in [("AoLP", clf.get("q_clf_aolp")), ("DoLP", clf.get("q_clf_dolp")),
                           ("Unpolarized", clf.get("q_clf_unpolarized"))]
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
    # Ergodic Control: driven by q7_mesh, q9_time, q5_materials/q8_defects,
    # and q1_robot_arms (all choices the user made affect the trajectory plan)
    # ------------------------------------------------------------------

    # q7: Mesh availability — core requirement for trajectory planning
    if answers.q7_mesh == "not_available":
        result["ergodic_control"]["impacts"].append(_impact(
            characteristic="No 3D mesh available",
            affects="Input",
            what_changes=(
                "Ergodic Control requires a 3D surface mesh to project trajectories. "
                "Without a mesh, trajectory planning falls back to 2D approximation only. "
                "Provide a mesh file path in the Ergodic Control configuration once available."
            ),
            action_type="review",
            reason="Q7: 3D mesh not available",
        ))
        result["ergodic_control"]["flags"].append(_flag(
            id="flag_ergodic_no_mesh",
            type="warning",
            message=(
                "No 3D mesh available. Ergodic trajectory planning will be limited to "
                "2D approximation until a mesh is provided."
            ),
            module_id="ergodic_control",
        ))
        total_characteristics += 1
    elif answers.q7_mesh == "in_preparation":
        result["ergodic_control"]["impacts"].append(_impact(
            characteristic="3D mesh in preparation",
            affects="Input",
            what_changes=(
                "Mesh is not yet available. Configure the mesh path in the Ergodic Control "
                "module config tab once the mesh is ready."
            ),
            action_type="review",
            reason="Q7: 3D mesh in preparation",
        ))
        result["ergodic_control"]["flags"].append(_flag(
            id="flag_ergodic_mesh_pending",
            type="human_oversight",
            message="3D mesh is in preparation — configure the mesh path before running compute.",
            module_id="ergodic_control",
        ))
        total_characteristics += 1

    # q9: Time constraints affect trajectory density
    if answers.q9_time == "tight":
        time_str = ""
        if answers.q9_time_value is not None:
            time_str = f" ({answers.q9_time_value} {answers.q9_time_unit or 'minutes'})"
        result["ergodic_control"]["impacts"].append(_impact(
            characteristic="Tight time budget",
            affects="Process",
            what_changes=(
                f"Tight time budget{time_str} constrains trajectory length. "
                "Adjust the time budget and trajectory density in the Ergodic Control "
                "configuration to ensure the trajectory fits within the allowed window."
            ),
            action_type="reconfigure",
            reason="Q9: Tight time constraints specified",
        ))
        total_characteristics += 1
    elif answers.q9_time == "none":
        result["ergodic_control"]["impacts"].append(_impact(
            characteristic="No time constraint",
            affects="Process",
            what_changes=(
                "No time budget specified — dense trajectory mode is available. "
                "Consider setting a high time budget in the Ergodic Control configuration "
                "to maximise surface coverage."
            ),
            action_type="reconfigure",
            reason="Q9: No time constraints",
        ))
        total_characteristics += 1

    # q5/q8: Material and defect context informs the prior distribution
    if answers.q5_materials or answers.q8_defects:
        mat_str = ", ".join(answers.q5_materials) if answers.q5_materials else "unspecified"
        def_str = ", ".join(answers.q8_defects) if answers.q8_defects else "unspecified"
        result["ergodic_control"]["impacts"].append(_impact(
            characteristic="Material / defect context updated",
            affects="Input",
            what_changes=(
                f"Target materials: {mat_str}. Defect types: {def_str}. "
                "The Ergodic Control prior distribution is seeded from this context — "
                "re-run compute to regenerate trajectory and Kalman configs."
            ),
            action_type="reconfigure",
            reason="Q5/Q8: Material or defect types specified",
        ))
        total_characteristics += 1

    # q1: Multiple robot arms require coordinated trajectory planning
    if answers.q1_robot_arms == "multiple":
        result["ergodic_control"]["impacts"].append(_impact(
            characteristic="Multiple robot arms",
            affects="Process",
            what_changes=(
                "Trajectory must be partitioned across multiple arms to avoid collisions "
                "and ensure complementary coverage. The ergodic optimisation must account "
                "for multi-agent coordination."
            ),
            action_type="reconfigure",
            reason="Q1: Multiple robot arms selected",
        ))
        result["ergodic_control"]["flags"].append(_flag(
            id="flag_ergodic_multi_arm",
            type="human_oversight",
            message=(
                "Multi-arm ergodic trajectory partitioning requires manual review. "
                "Verify that arm assignments are collision-free before deployment."
            ),
            module_id="ergodic_control",
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

    confidence = _compute_confidence(answers, module_answers)
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
        # Ergodic Control always requires configuration before compute
        if mid == "ergodic_control" and new_status == "ok":
            new_status = "needs_action"

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

def _compute_confidence(answers: QuestionnaireAnswers, module_answers: dict = None) -> Dict[str, Any]:
    if module_answers is None:
        module_answers = {}
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

    # Cat 5: Defect Types
    if answers.q8_defects:
        score += 1

    # Cat 6: Time / Profit
    if answers.q9_time or answers.q10_profit:
        score += 1

    # Cat 7: Mesh
    if answers.q7_mesh:
        score += 1

    # Cat 8: Grabber Hardware (now in module_answers["grabber"])
    _grab_conf = module_answers.get("grabber", {})
    if (_grab_conf.get("q_grab_force_sensor_ip") or _grab_conf.get("q_grab_lighting_mode")
            or _grab_conf.get("q_grab_arduino_path") or _grab_conf.get("q_grab_teensy_path")
            or answers.q2_camera_framerate):
        score += 1

    # Cat 9: Classifier Config — now sourced from module_answers["vision_classifier"]
    _clf_conf = module_answers.get("vision_classifier", {})
    if (_clf_conf.get("q_clf_model_path") or _clf_conf.get("q_clf_dataset_dir")
            or _clf_conf.get("q_clf_use_lasers") or _clf_conf.get("q_clf_threshold")
            or _clf_conf.get("q_clf_fps")):
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
