# Configuration Optimization Tool (COT)

Translates questionnaire answers about a MAGICIAN use case into per-module configuration and ROS 2 deployment commands.

## Language

**Setup**:
Identifies one calibration entry in the Localiser's calibration database (YAML), tying a use case to a saved base→mesh transform, robot links, and mesh. COT cannot read or validate the live database at answer-time — it only records which `setup` name a use case targets.
_Avoid_: cell, layout, config

**Registration**:
The manual, operator-and-robot procedure (VTK point-picking + TCP contact) that produces a Setup's stored transform. It happens outside COT and cannot be performed or verified by it — COT can only remind the operator that it's still required.
_Avoid_: calibration run, localisation

**Static broadcast mode**:
The Localiser republishes a Setup's saved transform unchanged as static TF. Mutually exclusive with dynamic broadcast mode.

**Dynamic broadcast mode**:
The Localiser adds a live slider displacement to a Setup's saved transform and publishes it as dynamic TF. Mutually exclusive with static broadcast mode.
