---
type: glossary
aliases:
  - glossary
  - domeintaal
tags:
  - glossary
  - domain
related:
  - "[[0003-separate-pipeline-selection-from-task-type]]"
  - "[[0004-module-scope-is-derived-without-manual-override]]"
---

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
A phase of the MAGICIAN architecture that a COT module belongs to: Defect Detection, Task Planning, Motion Planning, or Controller. Motion Planning holds the modules that produce motion references (Motion Planner, Ergodic Control, DMP); Controller holds the modules of the IIT grinding runtime that turn those references into robot commands (Cartesian Controller, Impedance Controller). Groups are fixed architecture metadata, not derived from questionnaire answers. On the dashboard, a dependency between two modules of the same group is drawn as a module arrow; dependencies between groups collapse into one group arrow. Arrows only show how modules relate; they do not detect conflicts or block configurations.
_Avoid_: category, section, phase (ambiguous with capability level)

**DMP**:
The grinding module that replays a learned grinding primitive on a detected defect. Belongs to the Motion Planning group, alongside but separate from the Motion Planner (whose own `discrete_dmp`/`rhytmic_dmp` services are not the DMP). In scope whenever the pipeline selection includes grinding.
_Avoid_: DMP Motion Planner, grinding planner

**Learned grinding primitive**:
What the DMP replays on a defect: a pose profile and a wrench (force) profile, learned offline from demonstrations; there is one per defect class. New demonstrations mean the primitive is regenerated and validated outside COT — never retrained, and never by COT itself.
_Avoid_: model, prototype (on its own), DMP (that is the module, not the primitive)

**IIT grinding runtime**:
The single process that hosts the DMP, Cartesian Controller and Impedance Controller. It is configured once at startup and restarted to change; COT cannot tune it live. The three are separate COT modules but share one startup configuration.
_Avoid_: IIT player, grinding module

**Runtime deploy**:
The deploy action of the IIT grinding runtime. It can be started from any of its three tiles and always does the same: it checks that all three modules are computed, not out of date, and free of deploy blockers and open required capabilities, then combines their results into one `params.yaml` and returns notes only (artifact path, restart the runtime, names not verified with IIT). COT never sets parameters on, starts or restarts the runtime.

**Shared runtime parameter**:
A startup parameter of the IIT grinding runtime that serves more than one of its modules (e.g. the control rate). It has one value for the whole runtime, edited in one place and shown wherever it applies.

**Defect class**:
The classification of a defect, used by both inspection and grinding. COT's canonical defect classes are Positive Dent and Negative Dent; a partner may also describe an other defect class. Each module that consumes defect classes maps them to its own interface labels (e.g. the DMP's POSITIVE/NEGATIVE); a defect class without a mapping in a module makes that module not deployable and is never silently dropped. While a module owner has not confirmed the interface, that module passes the canonical classes through with a "mapping not verified" note instead of a blocker. "No Defect" is a classifier outcome, not a defect class.
_Avoid_: defect type (too generic), dents/dirt/surface damage (the old, too-generic questionnaire values)

**Required capability**:
An input a module needs that is not tied to one provider module — e.g. the measured wrench for the Impedance Controller. It is satisfied by an in-scope module that provides it or by a declared external source; with neither, the configuration cannot be deployed. A required capability never pulls a module into scope, and is shown as a status on the consuming module rather than as a dashboard arrow.
_Avoid_: dependency (implies a fixed provider)

**External input requirement**:
A required consumer input — of a module dependency whose normal MAGICIAN provider is out of scope, or of a required capability without an in-scope provider — for which the partner must declare an external source and agree its interface. Examples: defect information for the Orienteering Solver in grinding-only, which must include each defect's defect class; the measured wrench for the Impedance Controller when no in-scope module provides it.

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

**Out of date**:
A compute result whose answers changed after it was computed: the general answers or the module's own answers differ from the fingerprint stored at compute, or there is no fingerprint at all. Answers of other modules never make it out of date, and reverting a change makes it current again. It is a property of the compute result, not a module status.
_Avoid_: stale, outdated status
