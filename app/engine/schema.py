"""
Questionnaire schema — single source of truth (previously in backend/routers/questionnaire.py).
Imported by both the GUI form renderer and the questionnaire engine.
"""

SCHEMA = {
    "sections": [
        {"id": "A", "title": "Robot Configuration"},
        {"id": "B", "title": "Sensors & Perception"},
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
                "Select whether your setup uses a single robot arm or multiple coordinated arms. "
                "Multiple arms are needed for tasks requiring parallel operations."
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
                    "label": "How many robot arms?",
                    "min": 2,
                    "max": 10,
                    "default": 2,
                },
            },
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
            "tooltip": "Target capture frequency. Rates above 10 Hz require RAM-backed storage (--ram flag).",
            "type": "number",
            "min": 1,
            "max": 200,
            "default": 10,
        },
        {
            "id": "q2_stream_shm",
            "section": "B",
            "title": "Stream frames to shared memory",
            "tooltip": "Publish camera frames to a POSIX shared-memory segment instead of (or alongside) writing"
                       "files. Required for the live classifier.",
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
            ],
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
            "tooltip": "Choose how to prioritise inspection areas.",
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
            "tooltip": "Neural network backbone used for tile classification. resnet18 is a good default; larger"
                       "models are more accurate but slower.",
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
            "tooltip": "Side length of the square tiles fed to the classifier. Must match the value used during"
                       "training. Smaller tiles are faster but capture less context.",
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
            "tooltip": "Pixel stride between tiles during live inference. Smaller values produce denser heatmaps but"
                       "increase computation.",
            "type": "number",
            "min": 1,
            "max": 128,
            "default": 18,
        },
        {
            "id": "q_clf_threshold",
            "title": "Detection confidence threshold",
            "tooltip": "Minimum softmax confidence required to register a tile as a defect. Tiles below this are"
                       "reassigned to the low-confidence class.",
            "type": "number",
            "min": 0.0,
            "max": 1.0,
            "default": 0.6,
        },
        {
            "id": "q_clf_fps",
            "title": "Target inference frame rate (FPS)",
            "tooltip": "Maximum frame rate for the live classifier. Set to 0 for unlimited.",
            "type": "number",
            "min": 0.0,
            "default": 23.0,
        },
        {
            "id": "q_clf_majority_voting",
            "title": "Enable majority voting",
            "tooltip": "Apply a 3×3 spatial majority-vote filter to smooth classifier predictions and suppress"
                       "isolated false positives.",
            "type": "select",
            "options": [
                {"value": "yes", "label": "Yes (recommended)"},
                {"value": "no",  "label": "No"},
            ],
        },
        {
            "id": "q_clf_two_stage",
            "title": "Enable two-stage ensemble classification",
            "tooltip": "Use a full model ensemble (binary filter → multi-class) for higher accuracy at the cost of"
                       "increased GPU usage.",
            "type": "select",
            "options": [
                {"value": "no",  "label": "No — single model (faster)"},
                {"value": "yes", "label": "Yes — two-stage ensemble (more accurate)"},
            ],
        },
        {
            "id": "q_clf_model_path",
            "title": "Path to pre-trained model checkpoint",
            "tooltip": "Absolute path to an existing .pth file. If provided, training is skipped. Leave empty to"
                       "generate a training configuration instead.",
            "type": "text",
            "placeholder": "/path/to/allclass_resnet18.pth",
        },
        {
            "id": "q_clf_dataset_dir",
            "title": "Training dataset directory",
            "tooltip": "Path to the annotated tile dataset (keras_dataset/ layout). Required only when no pre-trained"
                       "model is provided.",
            "type": "text",
            "placeholder": "/path/to/keras_dataset/",
            "condition": {"field": "q_clf_model_path", "operator": "empty"},
        },
        {
            "id": "q_clf_epochs",
            "title": "Training epochs",
            "tooltip": "Number of full passes over the training dataset.",
            "type": "number",
            "min": 1,
            "default": 10,
            "condition": {"field": "q_clf_model_path", "operator": "empty"},
        },
        {
            "id": "q_clf_batch_size",
            "title": "Training batch size",
            "tooltip": "Number of tiles per gradient update. Reduce if GPU memory is insufficient.",
            "type": "number",
            "min": 1,
            "default": 64,
            "condition": {"field": "q_clf_model_path", "operator": "empty"},
        },
        {
            "id": "q_clf_learning_rate",
            "title": "Learning rate",
            "tooltip": "AdamW optimiser learning rate.",
            "type": "number",
            "min": 1e-6,
            "default": 0.0005,
            "condition": {"field": "q_clf_model_path", "operator": "empty"},
        },
        {
            "id": "q_clf_loss",
            "title": "Training loss function",
            "tooltip": "focal loss handles class imbalance well; cross_entropy is simpler.",
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
            "tooltip": "Subscribe to distance sensor topics and fuse depth into detection messages using IDW"
                       "interpolation.",
            "type": "select",
            "options": [
                {"value": "yes", "label": "Yes — use laser depth fusion"},
                {"value": "no",  "label": "No — 2D detections only"},
            ],
        },
        {
            "id": "q_clf_laser_topic_1",
            "title": "Laser sensor topic 1",
            "tooltip": "ROS 2 topic for the first distance sensor.",
            "type": "text",
            "placeholder": "magician_grabber/distance1",
            "condition": {"field": "q_clf_use_lasers", "value": "yes"},
        },
        {
            "id": "q_clf_laser_topic_2",
            "title": "Laser sensor topic 2",
            "tooltip": "ROS 2 topic for the second distance sensor.",
            "type": "text",
            "placeholder": "magician_grabber/distance2",
            "condition": {"field": "q_clf_use_lasers", "value": "yes"},
        },
        {
            "id": "q_clf_laser_topic_3",
            "title": "Laser sensor topic 3",
            "tooltip": "ROS 2 topic for the third distance sensor.",
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
            "type": "number",
            "default": 320,
            "condition": {"field": "q_clf_use_lasers", "value": "yes"},
        },
        {
            "id": "q_clf_laser_px2_y",
            "title": "Laser 2 pixel position — Y",
            "type": "number",
            "default": 200,
            "condition": {"field": "q_clf_use_lasers", "value": "yes"},
        },
        {
            "id": "q_clf_laser_px3_x",
            "title": "Laser 3 pixel position — X",
            "type": "number",
            "default": 520,
            "condition": {"field": "q_clf_use_lasers", "value": "yes"},
        },
        {
            "id": "q_clf_laser_px3_y",
            "title": "Laser 3 pixel position — Y",
            "type": "number",
            "default": 200,
            "condition": {"field": "q_clf_use_lasers", "value": "yes"},
        },
        {
            "id": "q_clf_laser_idw_power",
            "title": "Laser IDW interpolation power",
            "tooltip": "Power parameter for Inverse Distance Weighting depth interpolation.",
            "type": "number",
            "min": 0.1,
            "default": 2.0,
            "condition": {"field": "q_clf_use_lasers", "value": "yes"},
        },
        # --- Advanced: polarization channel selection ---
        {
            "id": "q_clf_advanced",
            "title": "Configure advanced polarization channels",
            "tooltip": "AoLP, DoLP, and unpolarized are extra input channels derived from the 4 Stokes channels. These"
                       "are baked into the model at training time.",
            "type": "select",
            "options": [
                {"value": "no",  "label": "No — use standard 4-channel input"},
                {"value": "yes", "label": "Yes — configure advanced channel options"},
            ],
        },
        {
            "id": "q_clf_aolp",
            "title": "Include Angle of Linear Polarization (AoLP) channel",
            "tooltip": "Adds an AoLP-derived channel to the model input. Must match training configuration.",
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
            "tooltip": "Adds a DoLP-derived channel to the model input. Must match training configuration.",
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
            "tooltip": "Adds the mean of the 4 polarization channels as an extra input channel.",
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

ERGODIC_CONTROL_CONFIG = [
    {
        "id": "q_ergodic_mesh_path",
        "title": "Path to 3D mesh file (.stl)",
        "tooltip": "Absolute path to the .stl surface mesh. Used to project 2D trajectories to 3D end-effector poses.",
        "type": "text",
        "placeholder": "/path/to/surface.stl",
    },
    {
        "id": "q_ergodic_time_budget",
        "title": "Inspection time budget (seconds)",
        "tooltip": "Total time available for the inspection trajectory. Controls trajectory density and number of"
                   "waypoints.",
        "type": "number",
        "min": 1,
        "max": 3600,
        "default": 60,
    },
    {
        "id": "q_ergodic_trajectory_density",
        "title": "Trajectory waypoint density",
        "tooltip": "Sparse = fewer waypoints (faster), Dense = more waypoints (thorough coverage).",
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
        "tooltip": "Distance from end-effector to surface along the surface normal. Typically 0.05 m.",
        "type": "number",
        "min": 0.0,
        "max": 1.0,
        "default": 0,
    },
    {
        "id": "q_ergodic_use_historical",
        "title": "Use historical inspection data",
        "tooltip": "Incorporate defect locations from previous inspections as a prior distribution.",
        "type": "select",
        "options": [
            {"value": "yes", "label": "Yes — use historical defect data (recommended)"},
            {"value": "no",  "label": "No — start from uniform prior"},
        ],
    },
    {
        "id": "q_ergodic_use_welding_priors",
        "title": "Use welding process priors",
        "tooltip": "Add PLC welding data (spatter-prone weld seam locations) as high-probability regions in the prior.",
        "type": "select",
        "options": [
            {"value": "yes", "label": "Yes — include welding priors (recommended)"},
            {"value": "no",  "label": "No — ignore welding data"},
        ],
    },
    {
        "id": "q_ergodic_pdf_resolution",
        "title": "PDF grid resolution",
        "tooltip": "Resolution of the 2D probability density function grid. Higher = more accurate but slower"
                   "computation.",
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
        "tooltip": "Process noise variance. Higher = more trust in the motion model, less trust in the previous state.",
        "type": "number",
        "min": 0.0,
        "max": 10.0,
        "default": 0,
    },
    {
        "id": "q_ergodic_kalman_measurement_noise",
        "title": "Kalman measurement noise σ²",
        "tooltip": "Measurement noise variance. Higher = less trust in camera detections.",
        "type": "number",
        "min": 0.0,
        "max": 10.0,
        "default": 0,
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

GRABBER_CONFIG = [
    # ─ Camera tuning ──────────────────────────────────────────────────────────────────
    {
        "id": "q_grab_exposure",
        "title": "Camera exposure time (\u00b5s)",
        "tooltip": "Exposure time in microseconds (--exposure flag). Capped at 50 000 \u00b5s for hardware safety."
                   "Maps to GlobalConfig.exposure.",
        "type": "number",
        "min": 1,
        "max": 50000,
        "default": 5000,
    },
    {
        "id": "q_grab_gain",
        "title": "Camera gain",
        "tooltip": "Analogue gain of the GigE camera sensor (--gain flag). Maps to GlobalConfig.gain.",
        "type": "number",
        "min": 0.0,
        "default": 1.0,
    },
    {
        "id": "q_grab_blacklevel",
        "title": "Camera black-level offset",
        "tooltip": "Black-level offset applied to raw pixel values (--blacklevel flag). Maps to"
                   "GlobalConfig.blackLevel.",
        "type": "number",
        "min": 0.0,
        "default": 0.0,
    },
    # ─ Arduino (distance sensors + lighting controller) ────────────────────────
    {
        "id": "q_grab_arduino_path",
        "title": "Arduino serial port",
        "tooltip": "Serial device path for the Arduino that controls distance sensors and the lighting ring (--arduino"
                   "flag). Default: /dev/ttyUSB0.",
        "type": "text",
        "placeholder": "/dev/ttyUSB0",
    },
    {
        "id": "q_grab_lighting_mode",
        "title": "Lighting controller mode",
        "tooltip": "How the Arduino-controlled LED ring reacts on each captured frame. Maps to the --rlight / --dlight"
                   "/ --tlight / --trigger flags.",
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
        "tooltip": "Serial device path for the Teensy microcontroller that reads the accelerometer (--teensy flag)."
                   "Default: /dev/ttyACM0.",
        "type": "text",
        "placeholder": "/dev/ttyACM0",
    },
    # ─ ATI NetFT force/torque sensor ────────────────────────────────────────────
    {
        "id": "q_grab_force_sensor_ip",
        "title": "ATI NetFT sensor IP address",
        "tooltip": "IP address of the ATI NetFT force/torque sensor (--atiip flag). Maps to GlobalConfig.atiIP."
                   "Default: 192.168.137.201.",
        "type": "text",
        "placeholder": "192.168.137.201",
    },
    {
        "id": "q_grab_force_sensor_port",
        "title": "ATI NetFT sensor UDP port",
        "tooltip": "UDP port of the ATI NetFT sensor (--atiport flag). Maps to GlobalConfig.atiPort. Default: 49152.",
        "type": "number",
        "min": 1,
        "max": 65535,
        "default": 49152,
    },
    # ─ Tactile shared memory ───────────────────────────────────────────────────
    {
        "id": "q_grab_tactile_stream",
        "title": "Tactile shared memory stream name",
        "tooltip": "POSIX SHM stream name for tactile data (--tactilestream flag). Maps to"
                   "GlobalConfig.tactileStreamName. Default: stream_tactile.",
        "type": "text",
        "placeholder": "stream_tactile",
    },
    # ─ Operational flags (from common.h parse_arguments) ───────────────────────
    {
        "id": "q_grab_run_duration",
        "title": "Maximum capture duration (seconds)",
        "tooltip": "Hard stop time in seconds (--duration flag). Leave blank to run until manually stopped (--forever,"
                   "which is the default).",
        "type": "number",
        "min": 1,
        "max": 86400,
        "default": 0,
    },
    {
        "id": "q_grab_countdown",
        "title": "Countdown before capture starts (seconds)",
        "tooltip": "Number of seconds to count down before acquisition begins (--countdown flag). 0 to skip.",
        "type": "number",
        "min": 0,
        "max": 60,
        "default": 0,
    },
    {
        "id": "q_grab_compress",
        "title": "Compress camera frames to PNG",
        "tooltip": "Save frames as .png instead of raw .pnm (--compress flag). PNG is smaller but slower to write.",
        "type": "select",
        "options": [
            {"value": "no",  "label": "No \u2014 raw PNM (faster, larger files)"},
            {"value": "yes", "label": "Yes \u2014 PNG (smaller files, slower)"},
        ],
    },
    {
        "id": "q_grab_silent",
        "title": "Suppress progress output",
        "tooltip": "Do not print per-frame progress messages to stdout (--silent flag).",
        "type": "select",
        "options": [
            {"value": "no",  "label": "No \u2014 show progress"},
            {"value": "yes", "label": "Yes \u2014 silent"},
        ],
    },
    {
        "id": "q_grab_unixtime",
        "title": "Use Unix epoch timestamps",
        "tooltip": "Write Unix epoch (integer seconds) instead of human-readable timestamps in output files"
                   "(--unixtime flag).",
        "type": "select",
        "options": [
            {"value": "no",  "label": "No \u2014 human-readable timestamps"},
            {"value": "yes", "label": "Yes \u2014 Unix epoch timestamps"},
        ],
    },
]
