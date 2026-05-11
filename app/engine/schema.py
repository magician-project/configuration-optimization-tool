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
        {"id": 1, "label": "Robot Arms",      "fields": ["q1_robot_arms"]},
        {"id": 2, "label": "Camera/Sensors",  "fields": ["q2_camera_type", "q3_additional_sensors"]},
        {"id": 3, "label": "Lighting",        "fields": ["q4_lighting"]},
        {"id": 4, "label": "Material/Size",   "fields": ["q5_materials", "q6_object_size"]},
        {"id": 5, "label": "Defect Types",    "fields": ["q8_defects"]},
        {"id": 6, "label": "Time/Profit",     "fields": ["q9_time", "q10_profit"]},
        {"id": 7, "label": "Mesh",            "fields": ["q7_mesh"]},
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
            "id": "q3_additional_sensors",
            "section": "B",
            "title": "Additional sensor modalities needed",
            "tooltip": "Select additional sensors needed beyond vision.",
            "type": "checkbox",
            "options": [
                {"value": "tactile", "label": "Tactile / Force sensing"},
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
