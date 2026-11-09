"""
Module dependency register and configuration validation.

A dependency is a provider output that a consumer module needs. When the provider is out of
scope for the pipeline selection and external input is allowed, the partner must name an
external source and agree a contract (an "external input requirement"). A required capability
(REQUIRED_CAPABILITIES) is an input not tied to one provider module: an in-scope module or a
declared external source satisfies it. To add a dependency
or a module, add an entry below — validate_configuration() needs no change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Literal, NamedTuple, Optional, Tuple

from pydantic import BaseModel

from app.engine.module_registry import (
    MODULES, compute_default_modules, group_of, is_assessed, normalize_pipeline,
)
from app.models.use_case import ExternalSource, UseCase

# Architecture nodes that are not (yet) configurable COT modules. Register a node here
# before using it in a dependency; move it to MODULES once COT can configure it.
NON_COT_NODES: Dict[str, dict] = {
    "estimation_algorithm": {"name": "Estimation Algorithm"},
}

_NON_COT_NODES_BY_PIPELINE: Dict[str, List[str]] = {
    "inspection": ["estimation_algorithm"],
    "grinding": [],
    "both": ["estimation_algorithm"],
}


@dataclass(frozen=True)
class Dependency:
    id: str
    provider: str
    consumer: str
    provider_output: str
    consumer_input: str
    external_input_allowed: bool
    evidence_status: str      # documented | conceptual | proposed | unknown
    validation_status: str    # verified | owner_confirmation_needed
    external_schema: Optional[str] = None
    external_minimum_fields: Tuple[str, ...] = ()
    external_conditional_fields: Tuple[str, ...] = ()
    external_field_notes: Tuple[str, ...] = ()
    # Shown as an arrow on the dashboard only; never evaluated by validate_configuration().
    display_only: bool = False
    # False: the dependency is still validated, but no arrow is drawn for it.
    drawn: bool = True

    @property
    def verified(self) -> bool:
        return self.evidence_status == "documented" and self.validation_status == "verified"


class VisibleEdge(NamedTuple):
    provider: str
    consumer: str


class GroupEdge(NamedTuple):
    provider_group: str
    consumer_group: str


def _conceptual_edge(provider: str, consumer: str) -> Dependency:
    """Relation from the MAGICIAN documentation whose interface is not verified.

    Tactile/Vision -> Orienteering Solver simplify an indirect flow via the Estimation Algorithm,
    which is not a COT module and therefore not drawn. Orienteering Solver -> Motion Planner
    simplifies the flow via the Supervisor. Across groups they are drawn as one group arrow.
    """
    return Dependency(
        id=f"{provider}_to_{consumer}",
        provider=provider, consumer=consumer,
        provider_output="unspecified", consumer_input="unspecified",
        external_input_allowed=False,
        evidence_status="conceptual", validation_status="owner_confirmation_needed",
        display_only=True,
    )


# Only required, unconditional dependencies are validated: conditional ones are added once a
# questionnaire answer can evaluate their condition (otherwise they would leave every
# configuration incomplete). Dependencies with display_only=True are drawn on the dashboard
# but skipped by validation.
DEPENDENCIES: List[Dependency] = [
    Dependency(
        id="grabber_to_vision_classifier",
        provider="grabber", consumer="vision_classifier",
        provider_output="camera_frames", consumer_input="image_frames",
        external_input_allowed=True,
        evidence_status="documented", validation_status="verified",
    ),
    Dependency(
        id="grabber_to_tactile_classifier",
        provider="grabber", consumer="tactile_sensor",
        provider_output="tactile_sensor_data", consumer_input="tactile_sensor_features",
        external_input_allowed=True,
        evidence_status="documented", validation_status="verified",
    ),
    Dependency(
        id="estimation_to_orienteering_solver",
        provider="estimation_algorithm", consumer="orienteering_solver",
        provider_output="defect_list", consumer_input="defects",
        external_input_allowed=True,
        external_schema="external_inspection_handover",
        external_minimum_fields=(
            "defect.id", "defect.type", "defect.location.x", "defect.location.y", "defect.location.z",
            "defect.severity", "coordinate_frame.frame_id",
        ),
        external_conditional_fields=("defect.location.orientation", "defect.confidence"),
        external_field_notes=(
            "defect.type must be a defect class (positive_dent, negative_dent or other)",
            "coordinate_frame.frame_id must be a frame the Localiser publishes; for any other frame the "
            "handover must state the transform to the robot planning frame",
        ),
        evidence_status="documented", validation_status="verified",
    ),
    Dependency(
        id="orienteering_solver_to_dmp",
        provider="orienteering_solver", consumer="dmp",
        provider_output="grinding_schedule",
        consumer_input="ordered grinding targets (defect class, pose, frame_id)",
        external_input_allowed=False,
        evidence_status="documented", validation_status="verified",
    ),
    # IIT confirmed the architecture: DMP feeds both controllers (drawn as the group arrow
    # Motion Planning -> Controller). Impedance -> Cartesian is not in the confirmed diagram, so it
    # is neither drawn nor validated until IIT confirms it.
    Dependency(
        id="dmp_to_cartesian_controller",
        provider="dmp", consumer="cartesian_controller",
        provider_output="pose_profile", consumer_input="learned pose profile",
        external_input_allowed=False,
        evidence_status="documented", validation_status="verified",
    ),
    Dependency(
        id="dmp_to_impedance_controller",
        provider="dmp", consumer="impedance_controller",
        provider_output="force_profile", consumer_input="learned force profile",
        external_input_allowed=False,
        evidence_status="documented", validation_status="verified",
    ),
    Dependency(
        id="impedance_controller_to_cartesian_controller",
        provider="impedance_controller", consumer="cartesian_controller",
        provider_output="tcp_normal_corrections", consumer_input="TCP-normal displacement/velocity corrections",
        external_input_allowed=False,
        evidence_status="documented", validation_status="owner_confirmation_needed",
        display_only=True, drawn=False,
    ),
    _conceptual_edge("tactile_sensor", "orienteering_solver"),
    _conceptual_edge("vision_classifier", "orienteering_solver"),
    _conceptual_edge("orienteering_solver", "motion_planning"),
]


class ExternalInputRequirement(BaseModel):
    dependency_id: str   # the capability id for kind == "capability"
    consumer: str
    consumer_name: str
    input_name: str
    normal_provider: str = ""
    provider_name: str = ""
    # "dependency": the normal provider is out of scope. "capability": no in-scope module provides it.
    kind: Literal["dependency", "capability"] = "dependency"
    external_schema: Optional[str] = None
    minimum_fields: List[str] = []
    conditional_fields: List[str] = []
    field_notes: List[str] = []
    source_name: str = ""
    contract_agreed: bool = False
    schema_reference: str = ""

    @property
    def complete(self) -> bool:
        return bool(self.source_name.strip()) and self.contract_agreed


class CapabilityStatus(BaseModel):
    """How one required capability is satisfied; shown on the consuming module, never as an arrow."""
    capability: str
    consumer: str
    name: str
    provider: str = ""   # module id, "external", or "" when there is no valid source
    satisfied: bool
    summary: str
    blockers: List[str] = []


class ConfigurationValidation(BaseModel):
    # not_assessed | valid | valid_with_external_inputs | incomplete | invalid
    status: str
    satisfied: List[str] = []
    external_inputs: List[ExternalInputRequirement] = []
    owner_confirmation_needed: List[str] = []
    blocking: List[str] = []
    capabilities: List[CapabilityStatus] = []

    @property
    def capability_blockers(self) -> List[str]:
        return [b for c in self.capabilities for b in c.blockers]


def node_name(node_id: str) -> str:
    if node_id in MODULES:
        return MODULES[node_id]["name"]
    return NON_COT_NODES.get(node_id, {}).get("name", node_id)


GRABBER_WRENCH_TOPIC = "/magician_grabber/wrench_sensed"
DEFAULT_TARGET_FRAME = "fender"   # the Localiser's default mesh frame (q_local_mesh_link)


@dataclass(frozen=True)
class RequiredCapability:
    """An input a module needs that is not tied to one provider module (see CONTEXT.md).

    ``evaluate(in_scope, sensors, module_answers)`` returns the status and whether the partner must
    declare an external source. A capability never pulls a module into scope and is never drawn.
    """
    id: str
    consumer: str
    name: str
    evaluate: Callable[[set, List[str], Dict[str, dict]], Tuple["CapabilityStatus", bool]]
    external_fields: Tuple[str, ...] = ()


def _evaluate_measured_wrench(
    in_scope: set, sensors: List[str], module_answers: Dict[str, dict]
) -> Tuple[CapabilityStatus, bool]:
    config = module_answers.get("impedance_controller", {})
    choice = config.get("measured_wrench_source") or ""
    topic = str(config.get("measured_wrench_topic") or "").strip()
    # The Grabber only delivers F/T data when tactile sensing is selected (use_ati_force).
    grabber_in_scope = "grabber" in in_scope
    grabber_delivers = grabber_in_scope and "tactile" in sensors

    def status(provider: str, satisfied: bool, summary: str, *blockers: str) -> CapabilityStatus:
        return CapabilityStatus(
            capability="measured_wrench", consumer="impedance_controller", name="Measured wrench",
            provider=provider, satisfied=satisfied, summary=summary, blockers=list(blockers),
        )

    if choice not in ("", "grabber", "external"):
        return status(
            "", False, "Measured wrench: unsupported source",
            f"Measured wrench: unsupported source '{choice}'. Choose MAGICIAN Grabber or External.",
        ), False
    if choice == "grabber" and grabber_delivers:
        return status("grabber", True, f"Measured wrench: MAGICIAN Grabber ({topic or GRABBER_WRENCH_TOPIC})"), False
    if choice == "grabber":
        reason = (
            "the Grabber is not in scope for this pipeline selection" if not grabber_in_scope
            else "the Grabber only provides force/torque data when tactile sensing is selected"
        )
        return status(
            "", False, "Measured wrench: no valid source",
            f"Measured wrench: {reason}. Choose an external source or change the selection.",
        ), False
    if not choice and grabber_delivers:
        return status(
            "", False, "Measured wrench: source not chosen",
            "Measured wrench: choose a source (MAGICIAN Grabber or External).",
        ), False

    # External, or unanswered while the Grabber cannot be the source.
    blockers = [] if topic else ["Measured wrench: an external source needs a measured_wrench_topic."]
    return status(
        "external", bool(topic), f"Measured wrench: external ({topic or 'topic not set'})", *blockers
    ), True


def _evaluate_target_frame(
    in_scope: set, sensors: List[str], module_answers: Dict[str, dict]
) -> Tuple[CapabilityStatus, bool]:
    frame = str(module_answers.get("localiser", {}).get("q_local_mesh_link") or DEFAULT_TARGET_FRAME)
    if "localiser" in in_scope:
        return CapabilityStatus(
            capability="target_frame", consumer="dmp", name="Target frame", provider="localiser",
            satisfied=True, summary=f"Target frame: {frame} (Localiser)",
        ), False
    return CapabilityStatus(
        capability="target_frame", consumer="dmp", name="Target frame", satisfied=False,
        summary="Target frame: no provider",
        blockers=["Target frame: the Localiser is not in scope, so no frame is published."],
    ), False


REQUIRED_CAPABILITIES: List[RequiredCapability] = [
    RequiredCapability(
        "measured_wrench", "impedance_controller", "Measured wrench", _evaluate_measured_wrench,
        external_fields=("measured_wrench_topic",),
    ),
    RequiredCapability("target_frame", "dmp", "Target frame", _evaluate_target_frame),
]


def scope_for(pipeline: Optional[str], additional_sensors: Optional[List[str]] = None) -> List[str]:
    """Every architecture node in scope: the COT default module set plus non-COT nodes."""
    pipeline = normalize_pipeline(pipeline)
    return compute_default_modules(pipeline, additional_sensors) + _NON_COT_NODES_BY_PIPELINE[pipeline]


def _drawable_dependencies(in_scope_modules: Iterable[str]) -> List[Dependency]:
    """Dependencies between two in-scope COT modules, display-only ones included, unless not drawn.

    Non-COT nodes and out-of-scope modules never qualify (ADR-0004).
    """
    drawn = {m for m in in_scope_modules if m in MODULES}
    return [dep for dep in DEPENDENCIES if dep.drawn and dep.provider in drawn and dep.consumer in drawn]


def visible_dependency_edges(in_scope_modules: Iterable[str]) -> List[VisibleEdge]:
    """Module arrows: drawable dependencies between two modules of the same group."""
    return [
        VisibleEdge(dep.provider, dep.consumer)
        for dep in _drawable_dependencies(in_scope_modules)
        if group_of(dep.provider) == group_of(dep.consumer)
    ]


def visible_group_edges(in_scope_modules: Iterable[str]) -> List[GroupEdge]:
    """Group arrows: drawable dependencies across groups, collapsed to one arrow per group pair."""
    pairs = (
        (group_of(dep.provider), group_of(dep.consumer)) for dep in _drawable_dependencies(in_scope_modules)
    )
    return [GroupEdge(provider, consumer) for provider, consumer in dict.fromkeys(pairs) if provider != consumer]


def validate_configuration(
    pipeline: Optional[str],
    additional_sensors: Optional[List[str]] = None,
    external_sources: Optional[Dict[str, ExternalSource]] = None,
    module_answers: Optional[Dict[str, dict]] = None,
) -> ConfigurationValidation:
    """Pure function: check each in-scope consumer's required inputs against the pipeline scope."""
    if not is_assessed(pipeline):
        return ConfigurationValidation(status="not_assessed")
    external_sources = external_sources or {}
    in_scope = set(scope_for(pipeline, additional_sensors))
    result = ConfigurationValidation(status="valid")

    for dep in DEPENDENCIES:
        if dep.display_only or dep.consumer not in in_scope:
            continue

        if dep.provider in in_scope:
            if dep.verified:
                result.satisfied.append(dep.id)
            else:
                result.owner_confirmation_needed.append(dep.id)
            continue

        if not dep.external_input_allowed:
            result.blocking.append(dep.id)
            continue

        source = external_sources.get(dep.id) or ExternalSource()
        result.external_inputs.append(ExternalInputRequirement(
            dependency_id=dep.id,
            consumer=dep.consumer,
            consumer_name=node_name(dep.consumer),
            input_name=dep.consumer_input,
            normal_provider=dep.provider,
            provider_name=node_name(dep.provider),
            external_schema=dep.external_schema,
            minimum_fields=list(dep.external_minimum_fields),
            conditional_fields=list(dep.external_conditional_fields),
            field_notes=list(dep.external_field_notes),
            source_name=source.source_name,
            contract_agreed=source.contract_agreed,
            schema_reference=source.schema_reference,
        ))

    _evaluate_capabilities(result, in_scope, additional_sensors or [], module_answers or {}, external_sources)

    if result.blocking or result.capability_blockers:
        result.status = "invalid"
    elif result.owner_confirmation_needed or any(not r.complete for r in result.external_inputs):
        result.status = "incomplete"
    elif result.external_inputs:
        result.status = "valid_with_external_inputs"
    return result


def validate_use_case(use_case: UseCase) -> ConfigurationValidation:
    return validate_configuration(
        use_case.answers.q_pipeline, use_case.answers.q3_additional_sensors,
        use_case.external_sources, use_case.module_answers,
    )


def capability_deploy_blockers(validation: ConfigurationValidation, consumer: str) -> List[str]:
    """Why a consumer cannot be deployed: its capabilities have no valid source or an unnamed external one."""
    unnamed = [
        f"{r.input_name}: name the external source"
        for r in validation.external_inputs
        if r.consumer == consumer and r.kind == "capability" and not r.source_name.strip()
    ]
    return [b for c in validation.capabilities if c.consumer == consumer for b in c.blockers] + unnamed


def _evaluate_capabilities(
    result: ConfigurationValidation,
    in_scope: set,
    sensors: List[str],
    module_answers: Dict[str, dict],
    external_sources: Dict[str, ExternalSource],
) -> None:
    for capability in REQUIRED_CAPABILITIES:
        if capability.consumer not in in_scope:
            continue
        status, needs_external = capability.evaluate(in_scope, sensors, module_answers)
        if needs_external:
            source = external_sources.get(capability.id) or ExternalSource()
            req = ExternalInputRequirement(
                dependency_id=capability.id, consumer=capability.consumer,
                consumer_name=node_name(capability.consumer), input_name=capability.name.lower(),
                kind="capability", minimum_fields=list(capability.external_fields),
                source_name=source.source_name, contract_agreed=source.contract_agreed,
                schema_reference=source.schema_reference,
            )
            result.external_inputs.append(req)
            status.satisfied = status.satisfied and req.complete
            if status.satisfied:
                status.summary = f"{capability.name}: external source {req.source_name.strip()}"
            else:
                status.summary = f"{capability.name}: external input required"
        result.capabilities.append(status)
