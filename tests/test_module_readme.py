"""Documentation tab: README path derivation and empty-state, as pure functions."""

from pathlib import Path

import pytest

from app.engine.module_registry import (
    MODULES,
    README_EMPTY_STATE,
    load_module_readme,
    module_readme_path,
)


def test_readme_path_is_derived_from_compute_module(tmp_path):
    assert module_readme_path("grabber", root=tmp_path) == tmp_path / "modules" / "grabber" / "README.md"


def test_unknown_module_has_no_readme_path(tmp_path):
    assert module_readme_path("does_not_exist", root=tmp_path) is None


@pytest.mark.parametrize("module_id", sorted(MODULES))
def test_every_registered_module_has_a_readme_in_the_repo(module_id):
    path = module_readme_path(module_id)

    assert path is not None and path.is_file()


def test_readme_content_is_returned(tmp_path):
    readme = tmp_path / "modules" / "grabber" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text("# Grabber\n\nSensor driver.", encoding="utf-8")

    assert load_module_readme("grabber", root=tmp_path) == "# Grabber\n\nSensor driver."


def test_missing_readme_gives_empty_state(tmp_path):
    assert load_module_readme("grabber", root=tmp_path) == README_EMPTY_STATE


def test_unknown_module_gives_empty_state(tmp_path):
    assert load_module_readme("does_not_exist", root=tmp_path) == README_EMPTY_STATE


def test_unreadable_readme_gives_empty_state(tmp_path):
    readme = tmp_path / "modules" / "grabber" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_bytes(b"\xff\xfe\x00 not utf-8 \xc3\x28")

    assert load_module_readme("grabber", root=tmp_path) == README_EMPTY_STATE


def test_readme_that_is_a_directory_gives_empty_state(tmp_path):
    (tmp_path / "modules" / "grabber" / "README.md").mkdir(parents=True)

    assert load_module_readme("grabber", root=tmp_path) == README_EMPTY_STATE
