from __future__ import annotations

from pathlib import Path

from filedust import cli
from filedust.junk import Finding


def test_human_size_formats_units():
    assert cli.human_size(0) == "0.0 B"
    assert cli.human_size(1023) == "1023.0 B"
    assert cli.human_size(1024) == "1.0 KB"
    assert cli.human_size(1024 * 1024) == "1.0 MB"


def test_compute_total_size_counts_file_and_directory_findings(tmp_path):
    file_path = tmp_path / "file.tmp"
    file_path.write_bytes(b"1234")
    dir_path = tmp_path / "cache"
    dir_path.mkdir()
    (dir_path / "nested.tmp").write_bytes(b"12345")

    findings = [
        Finding(file_path, "file", "junk_file"),
        Finding(dir_path, "dir", "junk_dir"),
    ]

    assert cli.compute_total_size(findings) == 9


def test_delete_all_deletes_files_before_directories(tmp_path):
    directory = tmp_path / "__pycache__"
    directory.mkdir()
    nested_file = directory / "module.pyc"
    nested_file.write_text("x")
    file_path = tmp_path / "notes.tmp"
    file_path.write_text("x")

    findings = [
        Finding(directory, "dir", "junk_dir"),
        Finding(file_path, "file", "junk_file"),
    ]

    assert cli.delete_all(findings) == 0
    assert not file_path.exists()
    assert not directory.exists()


def test_delete_all_reports_directory_failures(tmp_path):
    missing_directory = tmp_path / "missing"

    failures = cli.delete_all([Finding(missing_directory, "dir", "junk_dir")])

    assert failures == 1


def test_main_refuses_paths_outside_home(fake_home, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()

    assert cli.main([str(outside), "--dry-run"]) == 1


def test_main_reports_missing_path_inside_home(fake_home):
    missing = fake_home / "missing"

    assert cli.main([str(missing), "--dry-run"]) == 1


def test_main_returns_zero_when_no_junk_found(fake_home):
    project = fake_home / "project"
    project.mkdir()
    (project / "keep.txt").write_text("x")

    assert cli.main([str(project), "--dry-run"]) == 0


def test_main_dry_run_reports_but_does_not_delete(fake_home):
    project = fake_home / "project"
    project.mkdir()
    junk_file = project / "notes.tmp"
    junk_file.write_text("x")

    assert cli.main([str(project), "--dry-run"]) == 0
    assert junk_file.exists()


def test_main_yes_deletes_without_prompt(fake_home, monkeypatch):
    project = fake_home / "project"
    project.mkdir()
    junk_file = project / "notes.tmp"
    junk_file.write_text("x")
    junk_dir = project / "__pycache__"
    junk_dir.mkdir()
    (junk_dir / "module.pyc").write_text("x")

    monkeypatch.setattr(
        cli.Confirm,
        "ask",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("confirmation should not be shown")
        ),
    )

    assert cli.main([str(project), "--yes"]) == 0
    assert not junk_file.exists()
    assert not junk_dir.exists()


def test_main_confirmation_decline_does_not_delete(fake_home, monkeypatch):
    project = fake_home / "project"
    project.mkdir()
    junk_file = project / "notes.tmp"
    junk_file.write_text("x")

    monkeypatch.setattr(cli.Confirm, "ask", lambda *args, **kwargs: False)

    assert cli.main([str(project)]) == 0
    assert junk_file.exists()


def test_main_confirmation_accept_deletes(fake_home, monkeypatch):
    project = fake_home / "project"
    project.mkdir()
    junk_file = project / "notes.tmp"
    junk_file.write_text("x")

    monkeypatch.setattr(cli.Confirm, "ask", lambda *args, **kwargs: True)

    assert cli.main([str(project)]) == 0
    assert not junk_file.exists()


def test_build_parser_defaults_to_current_directory():
    args = cli.build_parser().parse_args([])

    assert args.path == "."
    assert args.dry_run is False
    assert args.yes is False
