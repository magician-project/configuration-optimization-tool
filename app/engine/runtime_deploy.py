"""
runtime_deploy.py

Deploy of the IIT grinding runtime (ADR-0005). The DMP, Cartesian Controller and Impedance
Controller run in one process that is configured once at startup, so deploy is a runtime-level
action: whichever of the three tiles starts it, it checks all three and combines their compute
results into one ``params.yaml``. COT writes the file and gives notes; it never sets parameters
on, starts or restarts the runtime.

The node name is a placeholder and the parameter names are those of the partner specs: both are
Implemented, not Verified until IIT confirms them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

import yaml

from app.engine.module_dependencies import capability_deploy_blockers, validate_use_case
from app.engine.result_freshness import is_out_of_date
from app.engine.shared_parameters import shared_parameter_ids
from app.models.use_case import UseCase

RUNTIME_MODULES = ("dmp", "cartesian_controller", "impedance_controller")
RUNTIME_NODE = "iit_grinding_runtime_placeholder"
ARTIFACT_FILENAME = "params.yaml"


@dataclass
class RuntimeDeployment:
    artifact_path: str
    notes: List[str]


def is_runtime_module(module_id: str) -> bool:
    return module_id in RUNTIME_MODULES


def runtime_deploy_blockers(use_case: UseCase) -> List[str]:
    """Why the runtime cannot be deployed yet, over all three modules; empty when it can."""
    validation = validate_use_case(use_case)
    reasons: List[str] = []
    for module_id in RUNTIME_MODULES:
        ms = use_case.modules.get(module_id)
        if ms is None or ms.status in ("out_of_scope", "not_assessed"):
            reasons.append(f"{ms.module_name if ms else module_id} is not in scope for this use case")
            continue
        if ms.compute_result is None:
            reasons.append(f"{ms.module_name} is not computed")
            continue
        if is_out_of_date(use_case, module_id):
            reasons.append(f"{ms.module_name} result is out of date: Compute again")
            continue
        blockers = ms.compute_result.deploy_blockers
        if blockers is None:
            reasons.append(f"{ms.module_name} result predates deployment validation: Compute again")
            continue
        reasons.extend(
            f"{ms.module_name}: {blocker}"
            for blocker in blockers + capability_deploy_blockers(validation, module_id)
        )
    return reasons


def build_runtime_params(use_case: UseCase) -> dict:
    """The ROS 2 params document of the whole runtime, from the three compute results."""
    params: dict = {}
    for module_id in RUNTIME_MODULES:
        outputs = dict(use_case.modules[module_id].compute_result.outputs)
        # A shared parameter is written once, from its owner's result (see shared_parameters.py).
        for shared in shared_parameter_ids(module_id):
            outputs.pop(shared, None)
        for key, value in outputs.items():
            if key in params and params[key] != value:
                raise ValueError(f"{key} is set to different values by the runtime modules")
            params[key] = value
    return {RUNTIME_NODE: {"ros__parameters": params}}


def deploy_runtime(use_case: UseCase, output_dir: str) -> RuntimeDeployment:
    """Write the one startup artifact; raises ValueError (writing nothing) while the gate is not met.

    The previous artifact stays untouched unless the new one is complete: the document is built
    first and swapped in atomically, so a rejected or failed redeploy cannot leave an empty file.
    """
    reasons = runtime_deploy_blockers(use_case)
    if reasons:
        raise ValueError("IIT grinding runtime is not ready to deploy:\n- " + "\n- ".join(reasons))

    document = yaml.dump(build_runtime_params(use_case), default_flow_style=False, sort_keys=False)

    os.makedirs(output_dir, exist_ok=True)
    artifact_path = os.path.join(output_dir, ARTIFACT_FILENAME)
    temp_path = artifact_path + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(document)
        os.replace(temp_path, artifact_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    notes = [
        f"Startup artifact for the whole IIT grinding runtime: {artifact_path}",
        "Restart the IIT grinding runtime with this file; COT does not start, restart or tune it",
        "Parameter and node names are not verified with IIT",
    ]
    module_notes = (n for module_id in RUNTIME_MODULES for n in use_case.modules[module_id].compute_result.notes)
    return RuntimeDeployment(artifact_path, notes + list(dict.fromkeys(module_notes)))
