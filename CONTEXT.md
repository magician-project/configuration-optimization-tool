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

**Pipeline selection**:
The single questionnaire answer stating which MAGICIAN functionality a use case uses: `inspection`, `grinding`, or `both`. It determines the scope and default module set. Grinding does not imply MAGICIAN Inspection: grinding-only may use defect information from an external inspection source.
_Avoid_: task type, task mode, workflow type

**Default module set**:
The module ids relevant to a use case, derived from its pipeline selection and specific capability answers such as whether tactile sensing is used. Recomputed from the use-case answers rather than edited as a frozen snapshot.
_Avoid_: active modules (ambiguous with `ModuleState.status`), enabled modules

**In scope / Out of scope**:
Whether a module belongs to a use case's default module set. Derived only from questionnaire answers; a partner cannot switch an individual module on or off. An out-of-scope module produces no impacts or flags.
_Avoid_: enabled/disabled, on/off, override

**Module dependency**:
A required or conditional input relationship from a provider output to a consumer input. A dependency may be satisfied by an active MAGICIAN module or, when explicitly allowed, by a declared external input.

**Module group**:
A phase of the MAGICIAN architecture that a COT module belongs to: Defect Detection, Task Planning, or Motion Planning. Groups are fixed architecture metadata, not derived from questionnaire answers. On the dashboard, a dependency between two modules of the same group is drawn as a module arrow; dependencies between groups collapse into one group arrow. Arrows only show how modules relate; they do not detect conflicts or block configurations.
_Avoid_: category, section, phase (ambiguous with capability level)

**External input requirement**:
A required consumer input for which the normal MAGICIAN provider is inactive and an external source is allowed. For the initial grinding-only scenario, this is defect information required by the Orienteering Solver.

**Dependency evidence status**:
The confidence category attached to a dependency or interface: documented, conceptual, proposed, or unknown. This describes evidence, not whether a module is present in the COT or whether a use-case configuration is valid.

**Configuration validation status**:
The result of checking active modules and their required inputs: `valid`, `valid_with_external_inputs`, `incomplete`, or `invalid`. `valid_with_external_inputs` means complete for configuration, while receipt and validation of runtime data are a separate handover concern.

**Action required**:
A module status meaning the partner has at least one concrete open item for that module: an impact to handle, an unacknowledged flag, or an external input without an agreed source. A module with no open item is never "Action required", even if it still has to be validated before compute.
_Avoid_: using it for "not yet validated"

**Ready to validate**:
A module status for an in-scope module with no open item (no impact, unacknowledged flag, or pending external input) that the partner can still mark as validated before compute. Applies to every in-scope module, not only a fixed few.
_Avoid_: no action needed, ok

**Not assessed**:
The state of a use case whose pipeline selection is unanswered. The pipeline selection is the gate: until it is answered, scope cannot be derived, so no module is shown as in scope, valid, or free of actions, and impacts from other answers are not shown either.
_Avoid_: valid, no action needed (both claim an assessment that did not happen)
