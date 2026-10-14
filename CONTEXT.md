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

**Task type**:
A use case's answer to whether its robot arm only inspects, or also grinds/reworks. Grinding always implies inspection too — there is no grind-only scenario. Determines a use case's default module set.
_Avoid_: task mode, workflow type

**Default module set**:
The module ids relevant to a use case, derived from its task type (plus the tactile classifier when tactile sensing is selected). Recomputed from scratch on every save — never a frozen snapshot edited directly, and distinct from a per-module override a user applies on top of it. Advisory only: it never gates computation — a module outside it can still receive impacts and flags if the questionnaire answers trigger them.
_Avoid_: active modules (ambiguous with `ModuleState.status`), enabled modules

**Module override**:
A partner's explicit, per-module choice to force a module on or off, independent of the default module set. Persists on the use case across save/reload — including across later changes to task type or other answers, since it's a deliberate choice that must never be silently undone. Overriding a module off is a hard filter — it suppresses impacts, flags, and blocks compute/deploy entirely; overriding one on has no special computational effect since only override-off changes behaviour. A partner clears an override with an explicit "Reset to default" action, which removes the override entirely rather than flipping it — the module then goes back to following the default module set and ordinary impact computation.
_Avoid_: toggle (the UI control, not the domain concept), enable/disable (ambiguous with `ModuleState.status`)

**Disabled** (module status):
The `ModuleState.status` value a module gets once overridden off. Distinct from merely being absent from the default module set, which leaves a module's status untouched.
_Avoid_: inactive, off
