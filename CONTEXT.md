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

**Capability level**:
One of Phase 1 (decision support), Phase 2 (assisted configuration), or Phase 3 (advanced optimization) — describes what *kind* of automation a piece of COT functionality performs, independent of which release ships it. A single release may combine capability levels.
_Avoid_: phase (on its own, ambiguous with release phase), milestone

**Decision boundary**:
The line between what COT may do on its own (detect, explain, assist) and what a human must do (optimize across trade-offs, decide, resolve). A capability stays within the decision boundary as long as it only surfaces and explains information; it crosses the boundary the moment it resolves something autonomously. Cross-module conflict detection is in-boundary: COT may detect and explain a conflict, but a human resolves it.
_Avoid_: automation level, autonomy threshold

**Implemented / Verified / Supported**:
A three-step maturity ladder for any COT capability. _Implemented_: the code path exists and runs. _Verified_: it has been exercised against a representative live environment (e.g. a running ROS 2 node) and produces correct results. _Supported_: a Verified capability COT officially stands behind for a release — documented and safe for a partner to rely on. A capability can be Implemented without being Verified or Supported.
_Avoid_: tested (too vague — state which rung of the ladder)
