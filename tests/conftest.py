from __future__ import annotations

from pathlib import Path

import pytest

from filedust import junk


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()

    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setattr(junk, "HOME", home.resolve())

    return home
