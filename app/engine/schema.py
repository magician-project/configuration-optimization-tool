"""
Questionnaire schema — single source of truth (previously in backend/routers/questionnaire.py).
Imported by both the GUI form renderer and the questionnaire engine.
"""

SCHEMA = {
    "sections": [
        {"id": "A", "title": "Robot Configuration"},
        {"id": "B", "title": "Sensors & Perception",
         # Unanswered pipeline counts as "both", so the section stays visible then.
         "condition": {"field": "q_pipeline", "operator": "not_in", "values": ["grinding"]}},
        {"id": "C", "title": "Material & Surface Properties"},
        {"id": "D", "title": "Defect Detection"},
        {"id": "E", "title": "Time & Priority Constraints"},
    ],
    "confidence_categories": [
        {"id": 1, "label": "Robot Arms",        "fields": ["q1_robot_arms"]},
        {"id": 2, "label": "Camera/Sensors",
         "fields": ["q2_camera_type", "q3_additional_sensors", "q2_camera_resolution",
                    "q2_camera_framerate", "q2_stream_shm"]},
        {"id": 3, "label": "Lighting",          "fields": ["q4_lighting"]},
        {"id": 4, "label": "Material/Size",     "fields": ["q5_materials", "q6_object_size"]},
        {"id": 5, "label": "Defect Types",
         "fields": ["q8_defects", "q_clf_model", "q_clf_tile_size", "q_clf_threshold"]},
        {"id": 6, "label": "Time/Profit",       "fields": ["q9_time", "q10_profit"]},
        {"id": 7, "label": "Mesh",              "fields": ["q7_mesh"]},
        {"id": 8, "label": "Grabber Hardware",
         "fields": ["q2_camera_framerate", "q_grab_force_sensor_ip", "q_grab_lighting_mode",
                    "q_grab_arduino_path", "q_grab_teensy_path"]},
        {"id": 9, "label": "Classifier Config",
         "fields": ["q_clf_model", "q_clf_tile_size", "q_clf_threshold", "q_clf_model_path", "q_clf_use_lasers"]},
    ],
    "questions": [
        {
            "id": "q1_robot_arms",
            "section": "A",
            "title": "Number of robot arms",
            "tooltip": (
                "How many robot arms work together on one task. This counts arms per robot role, not the "
                "total in your setup: inspection and grinding each run on their own robot anyway."
            ),
            "help_text": (
                "**What your choice changes**\n\n"
                "- **Single:** each task (inspection, grinding) is done by one arm.\n"
                "- **Multiple:** several arms work on the same task and must be coordinated. The Grabber "
                "handles parallel sensor streams, the Orienteering Solver plans for a team of arms, "
                "Ergodic Control splits the path across arms and the Motion Planner needs one planner "
                "per arm.\n\n"
                "Inspection and grinding together (Both) always use two robots, the Sensing Robot and the "
                "Cleaning Robot. That alone is not \"multiple\": choose Single if each robot has one arm.\n\n"
                "**Example**\n\n"
                "Both, with one Sensing Robot and one Cleaning Robot: choose Single. Inspection only, with "
                "two arms scanning the same part at once: choose Multiple."
            ),
            "type": "select",
            "options": [
                {"value": "single",   "label": "Single robot arm"},
                {"value": "multiple", "label": "Multiple robot arms"},
            ],
            "follow_up": {
                "condition": {"field": "q1_robot_arms", "value": "multiple"},
                "question": {
                    "id": "q1_num_arms",
                    "type": "number",
                    "label": "How many arms work together?",
                    "min": 2,
                    "max": 10,
                    "default": 2,
                },
            },
        },
        {
            "id": "q_pipeline",
            "section": "A",
            "title": "MAGICIAN functionality used",
            "tooltip": (
                "Which MAGICIAN functionality does this use case use? This determines which modules "
                "are in scope by default."
            ),
            "help_text": (
                "**What your choice changes**\n\n"
                "- **Inspection only:** Grabber, Vision Classifier and Ergodic Control, plus the shared "
                "Localiser and Motion Planner.\n"
                "- **Grinding only:** Orienteering Solver, plus the shared modules. MAGICIAN Inspection "
                "is out of scope, so defect information must come from an external inspection source "
                "(an *external input requirement*). Agree on the source and data contract with whoever "
                "provides it.\n"
                "- **Inspection and grinding (both):** all of the above.\n\n"
                "The default module set is advisory: you can still adjust the scope afterwards.\n\n"
                "**Example**\n\n"
                "A partner inspects parts with their own vision system and only wants MAGICIAN to plan "
                "the grinding. Choose *Grinding only* and declare their system as the external source "
                "for defect information."
            ),
            "help_link": {"module": "orienteering_solver", "anchor": "external-defect-input-grinding-only"},
            "type": "select",
            "options": [
                {"value": "inspection", "label": "Inspection only"},
                {"value": "grinding",   "label": "Grinding only"},
                {"value": "both",       "label": "Inspection and grinding (both)"},
            ],
        },
        {
            "id": "q2_camera_type",
            "section": "B",
            "title": "Camera type",
            "tooltip": "Choose the type of camera system you are using.",
            "type": "select",
            "options": [
                {"value": "standard", "label": "Standard / Default camera"},
                {"value": "gige",     "label": "GiGE camera"},
                {"value": "other",    "label": "Other camera type"},
            ],
            "follow_up": {
                "condition": {"field": "q2_camera_type", "operator": "in", "values": ["gige", "other"]},
                "question": {
                    "id": "q2_camera_spec",
                    "type": "text",
                    "label": "Specify camera model / type:",
                    "placeholder": "e.g., Basler acA1920-40gc",
                },
            },
        },
        {
            "id": "q2_camera_resolution",
            "section": "B",
            "title": "Camera resolution",
            "tooltip": "Capture resolution in pixels. Used to configure the GigE camera width and height.",
            "type": "dimensions",
            "fields": [
                {"id": "width",  "label": "Width (px)"},
                {"id": "height", "label": "Height (px)"},
            ],
            "units": ["px"],
            "default_unit": "px",
        },
        {
            "id": "q2_camera_framerate",
            "section": "B",
            "title": "Target frame rate (Hz)",
            "tooltip": "Target capture frequency. Rates above 10 Hz require RAM-backed storage (memory instead of disk).",
            "type": "number",
            "min": 1,
            "max": 200,
            "default": 10,
        },
        {
            "id": "q2_stream_shm",
            "section": "B",
            "title": "Stream frames to shared memory",
            "tooltip": "Publish camera frames to shared memory (fast data sharing between programs on this computer) "
                       "instead of, or alongside, writing files. Required for the live classifier.",
            "type": "select",
            "options": [
                {"value": "yes", "label": "Yes — stream to shared memory"},
                {"value": "no",  "label": "No — file output only"},
            ],
            "follow_up": {
                "condition": {"field": "q2_stream_shm", "value": "yes"},
                "question": {
                    "id": "q2_stream_shm_name",
                    "type": "text",
                    "label": "Shared memory stream name:",
                    "placeholder": "stream1",
                },
            },
        },
        {
            "id": "q3_additional_sensors",
            "section": "B",
            "title": "Additional sensor modalities needed",
            "tooltip": "Select additional sensors needed beyond vision.",
            "type": "checkbox",
            "options": [
                {"value": "tactile", "label": "Tactile / Force sensing (ATI NetFT + Teensy accelerometer)"},
                {"value": "distance", "label": "Distance sensors (Arduino-controlled)"},
                {"value": "vision",  "label": "Additional vision sensors"},
            ],
        },
        {
            "id": "q4_lighting",
            "section": "B",
            "title": "Lighting conditions",
            "tooltip": "Indicate if ambient lighting is sufficient.",
            "type": "select",
            "options": [
                {"value": "sufficient",  "label": "Sufficient lighting"},
                {"value": "additional",  "label": "Need additional lighting"},
            ],
        },
        {
            "id": "q5_materials",
            "section": "C",
            "title": "Surface materials to work with",
            "tooltip": "Select all material types you need to inspect.",
            "type": "checkbox",
            "options": [
                {"value": "metal",   "label": "Metal (aluminum, steel)"},
                {"value": "wood",    "label": "Wood"},
                {"value": "plastic", "label": "Plastic"},
                {"value": "other",   "label": "Other materials"},
            ],
            "follow_up": {
                "condition": {"field": "q5_materials", "operator": "contains", "value": "other"},
                "question": {
                    "id": "q5_other_material",
                    "type": "text",
                    "label": "Specify other material types:",
                    "placeholder": "e.g., carbon fiber, composite...",
                },
            },
        },
        {
            "id": "q6_object_size",
            "section": "C",
            "title": "Object sizes",
            "tooltip": "Specify the typical size range of objects to inspect.",
            "type": "select",
            "options": [
                {"value": "small",    "label": "Small objects"},
                {"value": "large",    "label": "Large objects (e.g., boats, vehicles)"},
                {"value": "variable", "label": "Variable sizes"},
            ],
            "follow_up": {
                "condition": {"field": "q6_object_size", "operator": "in", "values": ["large", "variable"]},
                "question": {
                    "id": "q6_dimensions",
                    "type": "dimensions",
                    "label": "Approximate object dimensions:",
                    "fields": [
                        {"id": "length", "label": "Length"},
                        {"id": "width",  "label": "Width"},
                        {"id": "height", "label": "Height"},
                    ],
                    "units": ["m", "cm", "mm"],
                    "default_unit": "m",
                },
            },
        },
        {
            "id": "q7_mesh",
            "section": "C",
            "title": "3D mesh availability",
            "tooltip": "Indicate whether a 3D mesh or CAD model of the object is available.",
            "type": "select",
            "options": [
                {"value": "available",       "label": "Available"},
                {"value": "in_preparation",  "label": "In preparation"},
                {"value": "not_available",   "label": "Not available"},
            ],
            "follow_up": {
                "condition": {"field": "q7_mesh", "value": "in_preparation"},
                "question": {
                    "id": "q7_mesh_status",
                    "type": "select",
                    "label": "Current mesh status:",
                    "options": [
                        {"value": "cad",      "label": "CAD model exists"},
                        {"value": "scanning", "label": "Needs 3D scanning"},
                        {"value": "unknown",  "label": "Unknown"},
                    ],
                },
            },
        },
        {
            "id": "q8_defects",
            "section": "D",
            "title": "Types of defects to detect",
            "tooltip": "Select all defect types relevant to your application.",
            "type": "checkbox",
            "options": [
                {"value": "dents",          "label": "Dents / Deformations"},
                {"value": "dirt",           "label": "Dirt / Contamination"},
                {"value": "surface_damage", "label": "Surface damage"},
                {"value": "other",          "label": "Other defect types"},
            ],
            "follow_up": {
                "condition": {"field": "q8_defects", "operator": "contains", "value": "other"},
                "question": {
                    "id": "q8_other_defect",
                    "type": "text",
                    "label": "Specify other defect types:",
                    "placeholder": "e.g., corrosion, cracks...",
                },
            },
        },
        {
            "id": "q9_time",
            "section": "E",
            "title": "Time constraints",
            "tooltip": "Indicate if your inspection task has time limits.",
            "type": "select",
            "options": [
                {"value": "none",  "label": "No time constraints"},
                {"value": "tight", "label": "Tight deadlines / timeframe required"},
            ],
            "follow_up": {
                "condition": {"field": "q9_time", "value": "tight"},
                "question": {
                    "id": "q9_time_value",
                    "type": "number_with_unit",
                    "label": "Specify time constraint:",
                    "min": 0,
                    "default": 2,
                    "units": ["seconds", "minutes", "hours"],
                    "default_unit": "minutes",
                    "unit_field": "q9_time_unit",
                },
            },
        },
        {
            "id": "q10_profit",
            "section": "E",
            "title": "Profit / priority definition",
            "tooltip": (
                "Profit is the value the planner gives to visiting a defect or area. It decides which "
                "areas are inspected first when time is limited."
            ),
            "help_text": (
                "**What your choice changes**\n\n"
                "- **Standard:** the default profit model and service-time lookup for your materials "
                "and defect types. Nothing extra is needed from you.\n"
                "- **Custom:** replaces the default model. The planning problem may change to "
                "Orienteering with Variable Profits (OPVP), the profit calculator must be rewritten, "
                "and you must supply the profit function specification. This cannot be verified "
                "automatically, so a domain expert has to sign off.\n\n"
                "**Example**\n\n"
                "Weld seams should count twice as much as the surrounding plate because a defect there "
                "is more critical. That is a custom profit definition: have the responsible domain "
                "expert confirm the weighting."
            ),
            "help_link": {"module": "orienteering_solver", "anchor": "op-variant-selection-logic"},
            "type": "select",
            "options": [
                {"value": "standard", "label": "Standard profit calculation"},
                {"value": "custom",   "label": "Custom profit / priority criteria"},
            ],
        },
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# Vision Classifier module-specific configuration schema.
# These fields live in module_answers["vision_classifier"], NOT in the
# general questionnaire answers. Rendered in the Vision Classifier module
# detail panel.
# ─────────────────────────────────────────────────────────────────────────────

VISION_CLASSIFIER_CONFIG = [
        {
            "id": "q_clf_model",
            "title": "Classifier backbone architecture",
            "tooltip": "The neural network used to classify image tiles. ResNet-18 is a good starting point; larger "
                       "models can be more accurate but run slower. With a pre-trained model, pick the one it "
                       "was trained with.",
            "type": "select",
            "options": [
                {"value": "resnet18",          "label": "ResNet-18 (recommended)"},
                {"value": "resnext50",         "label": "ResNeXt-50"},
                {"value": "convnext_tiny",     "label": "ConvNeXt Tiny"},
                {"value": "efficientnet_v2_s", "label": "EfficientNet V2 S"},
                {"value": "swin_v2_t",         "label": "Swin Transformer V2 T"},
                {"value": "efficientnet_b0",   "label": "EfficientNet B0"},
                {"value": "mobilenet_v3_small", "label": "MobileNet V3 Small"},
                {"value": "custom_cnn",        "label": "Custom small CNN"},
            ],
        },
        {
            "id": "q_clf_tile_size",
            "title": "Classifier tile size (pixels)",
            "tooltip": "Side length, in pixels, of the square image tiles the classifier looks at. Must match the "
                       "tile size used during training. Smaller tiles run faster but see less context.",
            "type": "select",
            "options": [
                {"value": "32",  "label": "32 px (fast, less context)"},
                {"value": "48",  "label": "48 px (default)"},
                {"value": "64",  "label": "64 px (more context, slower)"},
                {"value": "128", "label": "128 px (high context, much slower)"},
            ],
        },
        {
            "id": "q_clf_step_size",
            "title": "Inference tile step size (pixels)",
            "tooltip": "Distance, in pixels, between neighbouring tiles during live inspection. Smaller steps give "
                       "a more detailed defect map but need more computing power. Default: 18.",
            "type": "number",
            "min": 1,
            "max": 128,
            "default": 18,
        },
        {
            "id": "q_clf_threshold",
            "title": "Detection confidence threshold",
            "tooltip": "Minimum confidence (0 to 1) for a tile to count as a defect; tiles below it are labelled "
                       "low-confidence instead. Raise it for fewer false alarms, lower it to miss fewer defects. "
                       "Default: 0.6.",
            "type": "number",
            "min": 0.0,
            "max": 1.0,
            "default": 0.6,
        },
        {
            "id": "q_clf_fps",
            "title": "Target inference frame rate (FPS)",
            "tooltip": "Maximum number of frames per second the live classifier processes. Use 0 for no limit. "
                       "Default: 23.",
            "type": "number",
            "min": 0.0,
            "default": 23.0,
        },
        {
            "id": "q_clf_majority_voting",
            "title": "Enable majority voting",
            "tooltip": "Smooths the results: each tile is decided together with its 3\u00d73 neighbours, which "
                       "removes isolated false alarms. Recommended.",
            "type": "select",
            "options": [
                {"value": "yes", "label": "Yes (recommended)"},
                {"value": "no",  "label": "No"},
            ],
        },
        {
            "id": "q_clf_two_stage",
            "title": "Enable two-stage ensemble classification",
            "tooltip": "Runs two models in sequence (first defect or no defect, then which type of defect) for "
                       "higher accuracy. Needs more GPU power.",
            "type": "select",
            "options": [
                {"value": "no",  "label": "No — single model (faster)"},
                {"value": "yes", "label": "Yes — two-stage ensemble (more accurate)"},
            ],
        },
        {
            "id": "q_clf_model_path",
            "title": "Path to pre-trained model checkpoint",
            "tooltip": "Full path to an already trained model file (.pth). If given, no training is needed. "
                       "Leave empty to prepare a training configuration instead.",
            "type": "text",
            "placeholder": "/path/to/allclass_resnet18.pth",
        },
        {
            "id": "q_clf_dataset_dir",
            "title": "Training dataset directory",
            "tooltip": "Folder with the annotated image tiles used for training (keras_dataset layout). Only "
                       "needed when no pre-trained model is given.",
            "type": "text",
            "placeholder": "/path/to/keras_dataset/",
            "condition": {"field": "q_clf_model_path", "operator": "empty"},
        },
        {
            "id": "q_clf_epochs",
            "title": "Training epochs",
            "tooltip": "How many times training goes through the whole dataset. More passes can improve "
                       "accuracy but take longer. Default: 10.",
            "type": "number",
            "min": 1,
            "default": 10,
            "condition": {"field": "q_clf_model_path", "operator": "empty"},
        },
        {
            "id": "q_clf_batch_size",
            "title": "Training batch size",
            "tooltip": "How many tiles are processed at once during training. Lower it if the GPU runs out of "
                       "memory. Default: 64.",
            "type": "number",
            "min": 1,
            "default": 64,
            "condition": {"field": "q_clf_model_path", "operator": "empty"},
        },
        {
            "id": "q_clf_learning_rate",
            "title": "Learning rate",
            "tooltip": "How big each training step is. Smaller values train slower but more stably. The default "
                       "suits most cases. Default: 0.0005.",
            "type": "number",
            "min": 1e-6,
            "default": 0.0005,
            "condition": {"field": "q_clf_model_path", "operator": "empty"},
        },
        {
            "id": "q_clf_loss",
            "title": "Training loss function",
            "tooltip": "How training measures its mistakes. Focal loss copes better when some defect types are "
                       "much rarer than others; cross-entropy is simpler.",
            "type": "select",
            "options": [
                {"value": "focal",         "label": "Focal loss (recommended for imbalanced classes)"},
                {"value": "cross_entropy", "label": "Cross-entropy"},
            ],
            "condition": {"field": "q_clf_model_path", "operator": "empty"},
        },
        {
            "id": "q_clf_use_lasers",
            "title": "Enable laser distance sensor fusion",
            "tooltip": "Combines the camera detections with the laser distance sensors, so each detection also "
                       "gets a depth (distance to the surface).",
            "type": "select",
            "options": [
                {"value": "yes", "label": "Yes — use laser depth fusion"},
                {"value": "no",  "label": "No — 2D detections only"},
            ],
        },
        {
            "id": "q_clf_laser_topic_1",
            "title": "Laser sensor topic 1",
            "tooltip": "Name of the ROS 2 topic (data channel) that delivers the readings of distance sensor 1.",
            "type": "text",
            "placeholder": "magician_grabber/distance1",
            "condition": {"field": "q_clf_use_lasers", "value": "yes"},
        },
        {
            "id": "q_clf_laser_topic_2",
            "title": "Laser sensor topic 2",
            "tooltip": "Name of the ROS 2 topic (data channel) that delivers the readings of distance sensor 2.",
            "type": "text",
            "placeholder": "magician_grabber/distance2",
            "condition": {"field": "q_clf_use_lasers", "value": "yes"},
        },
        {
            "id": "q_clf_laser_topic_3",
            "title": "Laser sensor topic 3",
            "tooltip": "Name of the ROS 2 topic (data channel) that delivers the readings of distance sensor 3.",
            "type": "text",
            "placeholder": "magician_grabber/distance3",
            "condition": {"field": "q_clf_use_lasers", "value": "yes"},
        },
        {
            "id": "q_clf_laser_px1_x",
            "title": "Laser 1 pixel position — X",
            "tooltip": "X coordinate (pixels) of laser 1 in the camera image plane.",
            "type": "number",
            "default": 120,
            "condition": {"field": "q_clf_use_lasers", "value": "yes"},
        },
        {
            "id": "q_clf_laser_px1_y",
            "title": "Laser 1 pixel position — Y",
            "tooltip": "Y coordinate (pixels) of laser 1 in the camera image plane.",
            "type": "number",
            "default": 200,
            "condition": {"field": "q_clf_use_lasers", "value": "yes"},
        },
        {
            "id": "q_clf_laser_px2_x",
            "title": "Laser 2 pixel position — X",
            "tooltip": "X coordinate (pixels) of laser 2 in the camera image plane.",
            "type": "number",
            "default": 320,
            "condition": {"field": "q_clf_use_lasers", "value": "yes"},
        },
        {
            "id": "q_clf_laser_px2_y",
            "title": "Laser 2 pixel position — Y",
            "tooltip": "Y coordinate (pixels) of laser 2 in the camera image plane.",
            "type": "number",
            "default": 200,
            "condition": {"field": "q_clf_use_lasers", "value": "yes"},
        },
        {
            "id": "q_clf_laser_px3_x",
            "title": "Laser 3 pixel position — X",
            "tooltip": "X coordinate (pixels) of laser 3 in the camera image plane.",
            "type": "number",
            "default": 520,
            "condition": {"field": "q_clf_use_lasers", "value": "yes"},
        },
        {
            "id": "q_clf_laser_px3_y",
            "title": "Laser 3 pixel position — Y",
            "tooltip": "Y coordinate (pixels) of laser 3 in the camera image plane.",
            "type": "number",
            "default": 200,
            "condition": {"field": "q_clf_use_lasers", "value": "yes"},
        },
        {
            "id": "q_clf_laser_idw_power",
            "title": "Laser IDW interpolation power",
            "tooltip": "Controls how strongly nearby lasers count more than distant ones when the depth between "
                       "lasers is estimated. Default: 2.0.",
            "type": "number",
            "min": 0.1,
            "default": 2.0,
            "condition": {"field": "q_clf_use_lasers", "value": "yes"},
        },
        # --- Advanced: polarization channel selection ---
        {
            "id": "q_clf_advanced",
            "title": "Configure advanced polarization channels",
            "tooltip": "Extra polarization-based input channels for the model (AoLP, DoLP, unpolarized "
                       "intensity). They are fixed at training time, so only change them to match the model you use.",
            "type": "select",
            "options": [
                {"value": "no",  "label": "No — use standard 4-channel input"},
                {"value": "yes", "label": "Yes — configure advanced channel options"},
            ],
        },
        {
            "id": "q_clf_aolp",
            "title": "Include Angle of Linear Polarization (AoLP) channel",
            "tooltip": "Adds the angle of linear polarization as an extra model input. Must match how the model "
                       "was trained.",
            "type": "select",
            "options": [
                {"value": "no",  "label": "No"},
                {"value": "yes", "label": "Yes"},
            ],
            "condition": {"field": "q_clf_advanced", "value": "yes"},
        },
        {
            "id": "q_clf_dolp",
            "title": "Include Degree of Linear Polarization (DoLP) channel",
            "tooltip": "Adds the degree of linear polarization as an extra model input. Must match how the model "
                       "was trained.",
            "type": "select",
            "options": [
                {"value": "no",  "label": "No"},
                {"value": "yes", "label": "Yes"},
            ],
            "condition": {"field": "q_clf_advanced", "value": "yes"},
        },
        {
            "id": "q_clf_unpolarized",
            "title": "Include unpolarized (mean intensity) channel",
            "tooltip": "Adds the average intensity of the 4 polarization channels as an extra model input. Must "
                       "match how the model was trained.",
            "type": "select",
            "options": [
                {"value": "no",  "label": "No"},
                {"value": "yes", "label": "Yes"},
            ],
            "condition": {"field": "q_clf_advanced", "value": "yes"},
        }
]


# ─────────────────────────────────────────────────────────────────────────────
# Ergodic Control module-specific configuration schema.
# These fields live in module_answers["ergodic_control"], NOT in the
# general questionnaire answers. Rendered in the Ergodic Control module
# detail panel.
# ─────────────────────────────────────────────────────────────────────────────

_ERGODIC_DOCS = {"module": "ergodic_control", "anchor": "inputs-from-questionnaire"}

ERGODIC_CONTROL_CONFIG = [
    {
        "id": "q_ergodic_mesh_path",
        "title": "Path to 3D mesh file (.stl)",
        "tooltip": "Full path to the 3D surface model (.stl) of the workpiece. Used to turn the planned 2D path "
                   "into 3D robot positions.",
        "help_link": _ERGODIC_DOCS,
        "type": "text",
        "placeholder": "/path/to/surface.stl",
    },
    {
        "id": "q_ergodic_time_budget",
        "title": "Inspection time budget (seconds)",
        "tooltip": "Total time available for the inspection path. A longer budget lets the planner use more "
                   "waypoints. Default: 60.",
        "help_link": _ERGODIC_DOCS,
        "type": "number",
        "min": 1,
        "max": 3600,
        "default": 60,
    },
    {
        "id": "q_ergodic_trajectory_density",
        "title": "Trajectory waypoint density",
        "tooltip": "Sparse uses fewer waypoints (faster); dense uses more (more thorough coverage).",
        "help_link": _ERGODIC_DOCS,
        "type": "select",
        "options": [
            {"value": "sparse", "label": "Sparse — 0.5× waypoints (faster)"},
            {"value": "normal", "label": "Normal — standard density (recommended)"},
            {"value": "dense",  "label": "Dense — 1.5× waypoints (thorough)"},
        ],
    },
    {
        "id": "q_ergodic_sensor_offset",
        "title": "Camera standoff distance (m)",
        "tooltip": "Distance between the robot tool (end-effector) and the surface, in metres, measured straight "
                   "out from the surface. Typically 0.05 m.",
        "help_link": _ERGODIC_DOCS,
        "type": "number_float",
        "min": 0.0,
        "max": 1.0,
        "decimals": 3,
        "step": 0.01,
        "default": 0.05,
    },
    {
        "id": "q_ergodic_use_historical",
        "title": "Use historical inspection data",
        "tooltip": "Uses defect locations from earlier inspections to focus the new inspection on places where "
                   "defects were found before.",
        "help_link": _ERGODIC_DOCS,
        "type": "select",
        "options": [
            {"value": "yes", "label": "Yes — use historical defect data (recommended)"},
            {"value": "no",  "label": "No — start from uniform prior"},
        ],
    },
    {
        "id": "q_ergodic_use_welding_priors",
        "title": "Use welding process priors",
        "tooltip": "Uses welding-process data from the PLC (places where weld spatter is likely) to focus the "
                   "inspection on those areas.",
        "help_link": _ERGODIC_DOCS,
        "type": "select",
        "options": [
            {"value": "yes", "label": "Yes — include welding priors (recommended)"},
            {"value": "no",  "label": "No — ignore welding data"},
        ],
    },
    {
        "id": "q_ergodic_pdf_resolution",
        "title": "PDF grid resolution",
        "tooltip": "Level of detail of the grid that describes where defects are likely. Finer grids are more "
                   "accurate but slower to compute.",
        "help_link": _ERGODIC_DOCS,
        "type": "select",
        "options": [
            {"value": "16",  "label": "16 × 16 (fastest)"},
            {"value": "32",  "label": "32 × 32 (recommended)"},
            {"value": "64",  "label": "64 × 64 (accurate, slower)"},
            {"value": "128", "label": "128 × 128 (high accuracy, slow)"},
        ],
    },
    {
        "id": "q_ergodic_kalman_process_noise",
        "title": "Kalman process noise σ²",
        "tooltip": "How uncertain the planner assumes its earlier estimate of the defect locations is. Higher "
                   "values make it adapt faster to new detections. Advanced setting.",
        "help_link": _ERGODIC_DOCS,
        "type": "number_float",
        "min": 0.0,
        "max": 10.0,
        "decimals": 3,
        "step": 0.05,
        "default": 0.1,
    },
    {
        "id": "q_ergodic_kalman_measurement_noise",
        "title": "Kalman measurement noise σ²",
        "tooltip": "How noisy the camera detections are assumed to be. Higher values mean the planner trusts "
                   "detections less. Advanced setting.",
        "help_link": _ERGODIC_DOCS,
        "type": "number_float",
        "min": 0.0,
        "max": 10.0,
        "decimals": 3,
        "step": 0.05,
        "default": 0.5,
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Grabber module-specific configuration schema.
# These fields live in module_answers["grabber"], NOT in the general
# questionnaire answers. Rendered in the Grabber module detail panel.
#
# Covers all hardware detail parameters from magician_grabber common.h that
# are purely grabber-internal: camera tuning, serial port paths, ATI NetFT
# network address, lighting mode, and operational flags.
# ─────────────────────────────────────────────────────────────────────────────

_GRABBER_DOCS = {"module": "grabber", "anchor": "module-specific-hardware-configuration-grabber-config-tab"}

GRABBER_CONFIG = [
    # ─ Camera tuning ──────────────────────────────────────────────────────────────────
    {
        "id": "q_grab_exposure",
        "title": "Camera exposure time (\u00b5s)",
        "tooltip": "How long the camera sensor collects light for each frame, in microseconds (\u00b5s). Raise it for "
                   "darker scenes; too high blurs moving parts. Maximum 50 000 \u00b5s. Default: 5000.",
        "help_link": _GRABBER_DOCS,
        "type": "number",
        "min": 1,
        "max": 50000,
        "default": 5000,
    },
    {
        "id": "q_grab_gain",
        "title": "Camera gain",
        "tooltip": "Amplifies the camera signal. Raise it for dark images, but a higher gain also adds image "
                   "noise. Default: 1.0.",
        "help_link": _GRABBER_DOCS,
        "type": "number",
        "min": 0.0,
        "default": 1.0,
    },
    {
        "id": "q_grab_blacklevel",
        "title": "Camera black-level offset",
        "tooltip": "Brightness offset applied to the raw camera image so that black looks truly black. Leave at "
                   "0.0 unless dark areas look washed out or clipped.",
        "help_link": _GRABBER_DOCS,
        "type": "number",
        "min": 0.0,
        "default": 0.0,
    },
    # ─ Arduino (distance sensors + lighting controller) ────────────────────────
    {
        "id": "q_grab_arduino_path",
        "title": "Arduino serial port",
        "tooltip": "Port name where the Arduino (distance sensors and lighting ring) is connected to the "
                   "computer. Change it only if the device shows up under a different name. "
                   "Default: /dev/ttyUSB0.",
        "help_link": _GRABBER_DOCS,
        "type": "text",
        "placeholder": "/dev/ttyUSB0",
    },
    {
        "id": "q_grab_lighting_mode",
        "title": "Lighting controller mode",
        "tooltip": "How the lighting ring behaves while frames are captured: off, cycling through the lights, "
                   "reacting to distance, following a pattern, or switching on a manual trigger after each frame.",
        "help_link": _GRABBER_DOCS,
        "type": "select",
        "options": [
            {"value": "none",    "label": "No automatic lighting control"},
            {"value": "rlight",  "label": "Round-robin (cycle through lights)"},
            {"value": "dlight",  "label": "Distance-based (react to distance sensors)"},
            {"value": "tlight",  "label": "Pattern-based"},
            {"value": "trigger", "label": "Manual trigger after each frame"},
        ],
    },
    # ─ Teensy (accelerometer) ─────────────────────────────────────────────────────────
    {
        "id": "q_grab_teensy_path",
        "title": "Teensy serial port",
        "tooltip": "Port name where the Teensy board (reads the accelerometer) is connected to the computer. "
                   "Change it only if the device shows up under a different name. Default: /dev/ttyACM0.",
        "help_link": _GRABBER_DOCS,
        "type": "text",
        "placeholder": "/dev/ttyACM0",
    },
    # ─ ATI NetFT force/torque sensor ────────────────────────────────────────────
    {
        "id": "q_grab_force_sensor_ip",
        "title": "ATI NetFT sensor IP address",
        "tooltip": "Network (IP) address of the ATI force/torque sensor. Must match the address configured on "
                   "the sensor. Default: 192.168.137.201.",
        "help_link": _GRABBER_DOCS,
        "type": "text",
        "placeholder": "192.168.137.201",
    },
    {
        "id": "q_grab_force_sensor_port",
        "title": "ATI NetFT sensor UDP port",
        "tooltip": "Network port used to talk to the ATI force/torque sensor. Only change it if the sensor was "
                   "set up with a different port. Default: 49152.",
        "help_link": _GRABBER_DOCS,
        "type": "number",
        "min": 1,
        "max": 65535,
        "default": 49152,
    },
    # ─ Tactile shared memory ───────────────────────────────────────────────────
    {
        "id": "q_grab_tactile_stream",
        "title": "Tactile shared memory stream name",
        "tooltip": "Name under which tactile sensor data is shared with other programs on this computer. Change "
                   "it only if a consuming program expects a different name. Default: stream_tactile.",
        "help_link": _GRABBER_DOCS,
        "type": "text",
        "placeholder": "stream_tactile",
    },
    # ─ Operational flags (from common.h parse_arguments) ───────────────────────
    {
        "id": "q_grab_run_duration",
        "title": "Maximum capture duration (seconds)",
        "tooltip": "Stops capturing automatically after this many seconds. Use 0 to keep capturing until you "
                   "stop it manually. Default: 0 (no limit).",
        "help_link": _GRABBER_DOCS,
        "type": "number",
        "min": 0,
        "max": 86400,
        "default": 0,
    },
    {
        "id": "q_grab_countdown",
        "title": "Countdown before capture starts (seconds)",
        "tooltip": "Seconds to wait before capturing starts, for example to get into position. Use 0 to start "
                   "immediately. Default: 0.",
        "help_link": _GRABBER_DOCS,
        "type": "number",
        "min": 0,
        "max": 60,
        "default": 0,
    },
    {
        "id": "q_grab_compress",
        "title": "Compress camera frames to PNG",
        "tooltip": "PNG gives smaller files; raw PNM is faster to write but larger. Choose raw when frame rate "
                   "matters more than disk space.",
        "help_link": _GRABBER_DOCS,
        "type": "select",
        "options": [
            {"value": "no",  "label": "No \u2014 raw PNM (faster, larger files)"},
            {"value": "yes", "label": "Yes \u2014 PNG (smaller files, slower)"},
        ],
    },
    {
        "id": "q_grab_silent",
        "title": "Suppress progress output",
        "tooltip": "Hides the progress message that is normally printed for every captured frame.",
        "help_link": _GRABBER_DOCS,
        "type": "select",
        "options": [
            {"value": "no",  "label": "No \u2014 show progress"},
            {"value": "yes", "label": "Yes \u2014 silent"},
        ],
    },
    {
        "id": "q_grab_unixtime",
        "title": "Use Unix epoch timestamps",
        "tooltip": "Stores timestamps in output files as a plain number (seconds since 1 January 1970) instead "
                   "of readable dates. Useful for automated processing.",
        "help_link": _GRABBER_DOCS,
        "type": "select",
        "options": [
            {"value": "no",  "label": "No \u2014 human-readable timestamps"},
            {"value": "yes", "label": "Yes \u2014 Unix epoch timestamps"},
        ],
    },
]

_LOCALISER_DOCS = {"module": "localiser", "anchor": "inputs-module_answerslocaliser"}

LOCALISER_CONFIG = [
    {
        "id": "q_local_setup",
        "title": "Calibration setup name",
        "tooltip": "Name of the calibration setup this use case uses, as entered by the operator during "
                   "Registration. It must match exactly; this tool cannot check it against the live database.",
        "help_link": _LOCALISER_DOCS,
        "type": "text",
        "placeholder": "cell_a",
    },
    {
        "id": "q_local_setup_registered",
        "title": "Has this setup already been registered?",
        "tooltip": "Choose No if this setup is not calibrated yet: Registration (matching CAD points to robot "
                   "positions) is then needed, which requires a mesh. Choose Yes to reuse an existing "
                   "calibration; no mesh is needed.",
        "help_link": _LOCALISER_DOCS,
        "type": "select",
        "options": [
            {"value": "no",  "label": "No \u2014 new setup, needs Registration"},
            {"value": "yes", "label": "Yes \u2014 reuse existing setup"},
        ],
        "default": "no",
    },
    {
        "id": "q_local_mesh_path",
        "title": "Workpiece CAD mesh path",
        "tooltip": "Full path to the workpiece CAD model (.stl) used during Registration. Only needed when the "
                   "setup above is not registered yet.",
        "help_link": _LOCALISER_DOCS,
        "type": "text",
        "placeholder": "/data/meshes/fender.stl",
    },
    {
        "id": "q_local_database_file",
        "title": "Calibration database file",
        "tooltip": "Path to the calibration file (calibration_data.yaml) that is read at startup. Note: the "
                   "current registration tool always writes to its default location, whatever is entered here.",
        "help_link": _LOCALISER_DOCS,
        "type": "text",
        "placeholder": "calibration_data.yaml",
    },
    {
        "id": "q_local_robot_base_link",
        "title": "Robot base link",
        "tooltip": "Name of the robot's base coordinate frame; the workpiece position is expressed relative to "
                   "it. Default: base_link.",
        "help_link": _LOCALISER_DOCS,
        "type": "text",
        "placeholder": "base_link",
    },
    {
        "id": "q_local_robot_ee_link",
        "title": "Robot end-effector link",
        "tooltip": "Name of the robot tool coordinate frame (TCP) whose position is recorded during "
                   "Registration. Default: tcp.",
        "help_link": _LOCALISER_DOCS,
        "type": "text",
        "placeholder": "tcp",
    },
    {
        "id": "q_local_mesh_link",
        "title": "Mesh TF frame",
        "tooltip": "Name of the coordinate frame that represents the workpiece, used to identify it. "
                   "Default: fender.",
        "help_link": _LOCALISER_DOCS,
        "type": "text",
        "placeholder": "fender",
    },
    {
        "id": "q_local_motion_mode",
        "title": "Broadcast mode",
        "tooltip": "Static keeps the calibrated workpiece position fixed. Dynamic also follows a live slider, "
                   "shifting the position as the slider moves. You can only use one of the two.",
        "help_link": _LOCALISER_DOCS,
        "type": "select",
        "options": [
            {"value": "static",  "label": "Static \u2014 republish the calibrated transform unchanged"},
            {"value": "dynamic", "label": "Dynamic \u2014 apply a live slider offset"},
        ],
        "default": "static",
    },
    {
        "id": "q_local_slider_topic",
        "title": "Slider position topic",
        "tooltip": "Name of the ROS 2 topic (data channel) that reports the slider's absolute position in "
                   "metres. Default: /slider/position_y.",
        "help_link": _LOCALISER_DOCS,
        "type": "text",
        "placeholder": "/slider/position_y",
        "condition": {"field": "q_local_motion_mode", "value": "dynamic"},
    },
    {
        "id": "q_local_slider_bias",
        "title": "Slider bias (m)",
        "tooltip": "Slider position (in metres) at which the workpiece sits at its calibrated pose. The applied "
                   "shift is the current slider value minus this bias.",
        "help_link": _LOCALISER_DOCS,
        "type": "number_float",
        "min": -10.0,
        "max": 10.0,
        "default": 0.0,
        "condition": {"field": "q_local_motion_mode", "value": "dynamic"},
    },
    {
        "id": "q_local_publish_rate_hz",
        "title": "Dynamic TF publish rate (Hz)",
        "tooltip": "How many times per second the slider-corrected workpiece position is updated. "
                   "Default: 30 Hz.",
        "help_link": _LOCALISER_DOCS,
        "type": "number",
        "min": 1,
        "max": 240,
        "default": 30,
        "condition": {"field": "q_local_motion_mode", "value": "dynamic"},
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Motion Planner module-specific configuration schema.
# These fields live in module_answers["motion_planning"], NOT in the general
# questionnaire answers. Rendered in the Motion Planner module detail panel.
#
# All fields map 1:1 to the "COT configuration parameters" table in section 4
# of COT_MOTION_PLANNER.md — real /motion_planner ROS 2 node parameters.
# ─────────────────────────────────────────────────────────────────────────────

_MP_DOCS = {"module": "motion_planning", "anchor": "inputs-module_answersmotion_planning"}

MOTION_PLANNER_CONFIG = [
    # ─ Reference frames ─────────────────────────────────────────────────────
    {
        "id": "q_mp_base_link",
        "title": "Robot base link",
        "tooltip": "Name of the robot's base coordinate frame; poses are converted into it. Default: base_link.",
        "help_link": _MP_DOCS,
        "type": "text",
        "placeholder": "base_link",
    },
    {
        "id": "q_mp_ee_link",
        "title": "End-effector link",
        "tooltip": "Name of the robot tool coordinate frame (TCP) that is controlled. Default: tcp.",
        "help_link": _MP_DOCS,
        "type": "text",
        "placeholder": "tcp",
    },
    {
        "id": "q_mp_ft_link",
        "title": "Force/torque sensor frame",
        "tooltip": "Name of the coordinate frame where the force/torque sensor is mounted. If left blank, the tool "
                   "frame is used.",
        "help_link": _MP_DOCS,
        "type": "text",
        "placeholder": "tcp",
    },
    # ─ Planner sampling ─────────────────────────────────────────────────────
    {
        "id": "q_mp_integration_dt",
        "title": "Planner sampling period (s)",
        "tooltip": "Time step of the planner output, in seconds. Smaller values give smoother motion but need "
                   "more computation. Default: 0.001 s.",
        "help_link": _MP_DOCS,
        "type": "number_float",
        "min": 0.0001,
        "max": 1.0,
        "decimals": 6,
        "step": 0.0001,
        "default": 0.001,
    },
    # ─ Z-admittance control tuning ──────────────────────────────────────────
    {
        "id": "q_mp_proportional_gain",
        "title": "Z-admittance proportional gain",
        "tooltip": "How strongly the Z-axis force controller reacts to the current force error (proportional "
                   "gain). Default: 1/3600 (\u2248 0.000278).",
        "help_link": _MP_DOCS,
        "type": "number_float",
        "min": 0.0,
        "decimals": 6,
        "step": 0.0001,
        "default": 0.000278,
    },
    {
        "id": "q_mp_integral_gain",
        "title": "Z-admittance integral gain",
        "tooltip": "How strongly the Z-axis force controller reacts to a force error that persists over time "
                   "(integral gain). Default: 4.6.",
        "help_link": _MP_DOCS,
        "type": "number_float",
        "min": 0.0,
        "default": 4.6,
    },
    {
        "id": "q_mp_integral_bound",
        "title": "Integral displacement bound (m)",
        "tooltip": "Upper limit, in metres, on the displacement the integral part of the force controller may "
                   "build up. Default: 0.02 m.",
        "help_link": _MP_DOCS,
        "type": "number_float",
        "min": 0.0,
        "default": 0.02,
    },
    {
        "id": "q_mp_integral_velocity_bound",
        "title": "Integral correction rate bound (m/s)",
        "tooltip": "Upper limit, in metres per second, on how fast the integral part of the force controller "
                   "may correct. Default: 0.01 m/s.",
        "help_link": _MP_DOCS,
        "type": "number_float",
        "min": 0.0,
        "default": 0.01,
    },
    # ─ Force/torque sensor sources ──────────────────────────────────────────
    {
        "id": "q_mp_mini58_topic",
        "title": "Mini58 force sensor topic",
        "tooltip": "Name of the ROS 2 topic (data channel) that delivers the ATI Mini58 force/torque readings. "
                   "Default: /ati_ft_sensor/wrench_sensed.",
        "help_link": _MP_DOCS,
        "type": "text",
        "placeholder": "/ati_ft_sensor/wrench_sensed",
    },
    {
        "id": "q_mp_nano17_topic",
        "title": "Nano17 force sensor topic",
        "tooltip": "Name of the ROS 2 topic (data channel) that delivers the ATI Nano17 force/torque readings. "
                   "Default: /magician_grabber/wrench_sensed.",
        "help_link": _MP_DOCS,
        "type": "text",
        "placeholder": "/magician_grabber/wrench_sensed",
    },
    {
        "id": "q_mp_impedance_sensor",
        "title": "Impedance/admittance force source",
        "tooltip": "Where the force measurement for impedance/admittance control comes from: the planner's own "
                   "force estimate (default) or one of the ATI sensors.",
        "help_link": _MP_DOCS,
        "type": "select",
        "options": [
            {"value": "force_estimate", "label": "Force estimate (default)"},
            {"value": "mini58",         "label": "ATI Mini58 sensor"},
            {"value": "nano17",         "label": "ATI Nano17 sensor"},
        ],
        "default": "force_estimate",
    },
    # ─ Diagnostics ───────────────────────────────────────────────────────────
    {
        "id": "q_mp_debug_prints",
        "title": "Enable debug prints",
        "tooltip": "Prints extra diagnostic messages while the planner runs. Only needed when troubleshooting. "
                   "Default: off.",
        "help_link": _MP_DOCS,
        "type": "select",
        "options": [
            {"value": "no",  "label": "No"},
            {"value": "yes", "label": "Yes"},
        ],
        "default": "no",
    },
    {
        "id": "q_mp_debug_lib",
        "title": "Enable library debug logging",
        "tooltip": "Prints extra diagnostic messages from the underlying motion library. Only needed when "
                   "troubleshooting. Default: off.",
        "help_link": _MP_DOCS,
        "type": "select",
        "options": [
            {"value": "no",  "label": "No"},
            {"value": "yes", "label": "Yes"},
        ],
        "default": "no",
    },
]
