"""
Module dependency register and configuration validation.

A dependency is a provider output that a consumer module needs. When the provider is out of
scope for the pipeline selection and external input is allowed, the partner must name an
external source and agree a contract (an "external input requirement"). To add a dependency
or a module, add an entry below — validate_configuration() needs no change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, NamedTuple, Optional, Tuple

from pydantic import BaseModel

from app.engine.module_registry import (
    MODULES, compute_default_modules, group_of, is_assessed, normalize_pipeline,
)
from app.models.use_case import ExternalSource

# Architecture nodes that are not (yet) configurable COT modules. Register a node here
# before using it in a dependency; move it to MODULES once COT can configure it.
NON_COT_NODES: Dict[str, dict] = {
    "estimation_algorithm": {"name": "Estimation Algorithm"},
    "dmp_motion_planner": {"name": "DMP Motion Planner"},
}

_NON_COT_NODES_BY_PIPELINE: Dict[str, List[str]] = {
    "inspection": ["estimation_algorithm"],
    "grinding": ["dmp_motion_planner"],
    "both": ["estimation_algorithm", "dmp_motion_planner"],
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
    # Shown as an arrow on the dashboard only; never evaluated by validate_configuration().
    display_only: bool = False

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
            "defect.id", "defect.location.x", "defect.location.y", "defect.location.z",
            "defect.severity",
        ),
        external_conditional_fields=(
            "defect.type", "defect.location.orientation", "defect.confidence",
            "coordinate_frame.frame_id",
        ),
        evidence_status="documented", validation_status="verified",
    ),
    Dependency(
        id="orienteering_solver_to_dmp",
        provider="orienteering_solver", consumer="dmp_motion_planner",
        provider_output="grinding_schedule", consumer_input="ordered_grinding_targets",
        external_input_allowed=False,
        evidence_status="documented", validation_status="verified",
    ),
    _conceptual_edge("tactile_sensor", "orienteering_solver"),
    _conceptual_edge("vision_classifier", "orienteering_solver"),
    _conceptual_edge("orienteering_solver", "motion_planning"),
]


class ExternalInputRequirement(BaseModel):
    dependency_id: str
    consumer: str
    consumer_name: str
    input_name: str
    normal_provider: str
    provider_name: str
    external_schema: Optional[str] = None
    minimum_fields: List[str] = []
    conditional_fields: List[str] = []
    source_name: str = ""
    contract_agreed: bool = False
    schema_reference: str = ""

    @property
    def complete(self) -> bool:
        return bool(self.source_name.strip()) and self.contract_agreed


class ConfigurationValidation(BaseModel):
    # not_assessed | valid | valid_with_external_inputs | incomplete | invalid
    status: str
    satisfied: List[str] = []
    external_inputs: List[ExternalInputRequirement] = []
    owner_confirmation_needed: List[str] = []
    blocking: List[str] = []


def node_name(node_id: str) -> str:
    if node_id in MODULES:
        return MODULES[node_id]["name"]
    return NON_COT_NODES.get(node_id, {}).get("name", node_id)


def scope_for(pipeline: Optional[str], additional_sensors: Optional[List[str]] = None) -> List[str]:
    """Every architecture node in scope: the COT default module set plus non-COT nodes."""
    pipeline = normalize_pipeline(pipeline)
    return compute_default_modules(pipeline, additional_sensors) + _NON_COT_NODES_BY_PIPELINE[pipeline]


def _drawable_dependencies(in_scope_modules: Iterable[str]) -> List[Dependency]:
    """Dependencies between two in-scope COT modules, display-only ones included.

    Non-COT nodes and out-of-scope modules never qualify (ADR-0004).
    """
    drawn = {m for m in in_scope_modules if m in MODULES}
    return [dep for dep in DEPENDENCIES if dep.provider in drawn and dep.consumer in drawn]


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
            source_name=source.source_name,
            contract_agreed=source.contract_agreed,
            schema_reference=source.schema_reference,
        ))

    if result.blocking:
        result.status = "invalid"
    elif result.owner_confirmation_needed or any(not r.complete for r in result.external_inputs):
        result.status = "incomplete"
    elif result.external_inputs:
        result.status = "valid_with_external_inputs"
    return result
