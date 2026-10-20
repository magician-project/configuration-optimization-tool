"""Documentation tab: README path derivation and empty-state, as pure functions."""

from pathlib import Path

import pytest

from app.engine.module_registry import (
    MODULES,
    README_EMPTY_STATE,
    load_module_readme,
    module_readme_path,
    resolve_readme_link,
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


def _repo(tmp_path):
    (tmp_path / "modules" / "localiser").mkdir(parents=True)
    (tmp_path / "CONTEXT.md").write_text("ctx", encoding="utf-8")
    (tmp_path / "modules" / "README.md").write_text("modules", encoding="utf-8")
    return tmp_path


def test_relative_link_is_resolved_against_the_readme_location(tmp_path):
    root = _repo(tmp_path)

    assert resolve_readme_link("localiser", "../../CONTEXT.md", root=root) == root / "CONTEXT.md"
    assert resolve_readme_link("localiser", "../README.md", root=root) == root / "modules" / "README.md"


def test_link_fragment_and_percent_encoding_are_handled(tmp_path):
    root = _repo(tmp_path)
    (root / "modules" / "my notes.md").write_text("x", encoding="utf-8")

    assert resolve_readme_link("localiser", "../README.md#usage", root=root) == root / "modules" / "README.md"
    assert resolve_readme_link("localiser", "../my%20notes.md", root=root) == root / "modules" / "my notes.md"


@pytest.mark.parametrize("href", [
    "../../../outside.md",
    "../../../../etc/passwd",
    "../missing.md",
    "#usage",
    "",
    "https://example.com/doc.md",
    "file:///etc/passwd",
    "C:/Windows/win.ini",
    "/etc/passwd",
])
def test_unresolvable_or_unsafe_links_are_rejected(tmp_path, href):
    root = _repo(tmp_path)
    (tmp_path.parent / "outside.md").write_text("x", encoding="utf-8")

    assert resolve_readme_link("localiser", href, root=root) is None


def test_link_in_unknown_module_is_rejected(tmp_path):
    assert resolve_readme_link("does_not_exist", "../README.md", root=_repo(tmp_path)) is None
