from __future__ import annotations

import os
from pathlib import Path

import pytest

from filedust.junk import (
    UserRules,
    iter_junk,
    load_user_rules,
    matches_any,
)


def finding_map(findings, home: Path) -> dict[str, tuple[str, str]]:
    return {
        str(f.path.relative_to(home)): (f.kind, f.reason) for f in findings
    }


def test_matches_any_supports_exact_star_globstar_and_stripped_slashes():
    assert matches_any(["Projects/App"], Path("Projects/App"))
    assert matches_any(["Projects/*"], Path("Projects/App"))
    assert not matches_any(["Projects/*"], Path("Projects/App/file.tmp"))
    assert matches_any(["Projects/**"], Path("Projects/App/file.tmp"))
    assert matches_any(["/Projects/**/"], Path("Projects/App/file.tmp"))
    assert matches_any(["Projects/**"], Path("Projects"))


def test_matches_any_is_case_sensitive():
    assert matches_any(["Projects/App"], Path("Projects/App"))
    assert not matches_any(["projects/app"], Path("Projects/App"))


def test_matches_any_returns_false_for_empty_patterns():
    assert not matches_any([], Path("anything"))


def test_load_user_rules_reads_case_preserved_include_and_exclude(fake_home):
    (fake_home / ".filedust.conf").write_text(
        "[include]\n"
        "CaseSensitive.TMP\n"
        "Projects/**/Build\n"
        "\n"
        "[exclude]\n"
        "Projects/Important\n",
        encoding="utf-8",
    )

    rules = load_user_rules()

    assert rules.include == ["CaseSensitive.TMP", "Projects/**/Build"]
    assert rules.exclude == ["Projects/Important"]


def test_load_user_rules_returns_empty_rules_without_config(fake_home):
    rules = load_user_rules()

    assert rules.include == []
    assert rules.exclude == []


def test_iter_junk_detects_builtin_junk_directories_and_files(fake_home):
    project = fake_home / "project"
    (project / "__pycache__").mkdir(parents=True)
    (project / "__pycache__" / "module.pyc").write_text("x")
    (project / ".pytest_cache").mkdir()
    (project / "notes.tmp").write_text("x")
    (project / "keep.txt").write_text("x")

    findings = finding_map(iter_junk(project), fake_home)

    assert findings == {
        "project/__pycache__": ("dir", "junk_dir"),
        "project/.pytest_cache": ("dir", "junk_dir"),
        "project/notes.tmp": ("file", "junk_file"),
    }


def test_iter_junk_does_not_descend_into_builtin_junk_directories(fake_home):
    project = fake_home / "project"
    (project / "__pycache__" / "nested").mkdir(parents=True)
    (project / "__pycache__" / "nested" / "extra.tmp").write_text("x")

    findings = finding_map(iter_junk(project), fake_home)

    assert findings == {"project/__pycache__": ("dir", "junk_dir")}


def test_iter_junk_exclude_rules_win_over_builtin_and_include_rules(fake_home):
    project = fake_home / "project"
    (project / "__pycache__").mkdir(parents=True)
    (project / "__pycache__" / "module.pyc").write_text("x")
    (project / "delete.tmp").write_text("x")
    (project / "keep.tmp").write_text("x")

    rules = UserRules()
    rules.include = ["project/**"]
    rules.exclude = ["project/__pycache__", "project/keep.tmp"]

    findings = finding_map(iter_junk(project, rules=rules), fake_home)

    assert findings == {"project/delete.tmp": ("file", "user_include")}


def test_iter_junk_user_include_can_select_custom_files_and_dirs(fake_home):
    project = fake_home / "project"
    (project / "custom-dir").mkdir(parents=True)
    (project / "custom-dir" / "nested.tmp").write_text("x")
    (project / "custom.file").write_text("x")

    rules = UserRules()
    rules.include = ["project/custom-dir", "project/custom.file"]

    findings = finding_map(iter_junk(project, rules=rules), fake_home)

    assert findings == {
        "project/custom-dir": ("dir", "user_include"),
        "project/custom.file": ("file", "user_include"),
    }


def test_iter_junk_skips_protected_directories_by_default(fake_home):
    project = fake_home / "project"
    (project / ".git" / "objects").mkdir(parents=True)
    (project / ".git" / "objects" / "junk.tmp").write_text("x")

    assert list(iter_junk(project)) == []


def test_iter_junk_reports_explicitly_included_protected_directory(fake_home):
    project = fake_home / "project"
    (project / ".git" / "objects").mkdir(parents=True)
    (project / ".git" / "objects" / "junk.tmp").write_text("x")

    rules = UserRules()
    rules.include = ["project/.git"]

    findings = finding_map(iter_junk(project, rules=rules), fake_home)
    assert findings == {"project/.git": ("dir", "user_include")}


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlinks unsupported")
def test_iter_junk_does_not_follow_valid_symlink_files(fake_home):
    project = fake_home / "project"
    project.mkdir()
    target = project / "real.txt"
    target.write_text("important")
    (project / "link.tmp").symlink_to(target)

    assert list(iter_junk(project)) == []


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlinks unsupported")
def test_iter_junk_allows_user_include_for_valid_symlink_files(fake_home):
    project = fake_home / "project"
    project.mkdir()
    target = project / "real.txt"
    target.write_text("important")
    (project / "link.txt").symlink_to(target)

    rules = UserRules()
    rules.include = ["project/link.txt"]

    findings = finding_map(iter_junk(project, rules=rules), fake_home)
    assert findings == {"project/link.txt": ("file", "user_include")}


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlinks unsupported")
def test_iter_junk_reports_broken_symlink_matching_junk_file_pattern(
    fake_home,
):
    project = fake_home / "project"
    project.mkdir()
    (project / "broken.tmp").symlink_to(project / "missing-target")

    findings = finding_map(iter_junk(project), fake_home)
    assert findings == {"project/broken.tmp": ("file", "broken_symlink")}


def test_iter_junk_skips_roots_outside_home(fake_home, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "junk.tmp").write_text("x")

    assert list(iter_junk(outside)) == []
