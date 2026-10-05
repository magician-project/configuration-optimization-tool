"""
Tests for ComputeResult.deploy_blockers: legacy results (predating this
field) must parse to None, distinguishable from a module that evaluated
blockers and found none ([]).
"""

from app.models.use_case import ComputeResult


def test_legacy_result_without_deploy_blockers_parses_as_none():
    result = ComputeResult(module_id="localiser", success=True, outputs={})
    assert result.deploy_blockers is None


def test_explicit_empty_deploy_blockers_is_preserved():
    result = ComputeResult(module_id="localiser", success=True, outputs={}, deploy_blockers=[])
    assert result.deploy_blockers == []


def test_explicit_deploy_blockers_are_preserved():
    result = ComputeResult(
        module_id="localiser", success=True, outputs={},
        deploy_blockers=["a setup name is required"],
    )
    assert result.deploy_blockers == ["a setup name is required"]
