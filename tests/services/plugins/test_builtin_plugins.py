from datetime import date, datetime
from pathlib import Path

import pytest

from shc.services.plugins.builtin_plugins import (
    complete_path,
    cwd,
    empty_list,
    empty_tuple,
    home,
    now,
    today,
)


def test_default_factories() -> None:
    assert empty_list() == []
    assert empty_list() is not empty_list()
    assert empty_tuple() == ()
    assert cwd() == Path.cwd()
    assert home() == Path.home()
    assert isinstance(today(), date)
    assert now().tzinfo is not None
    assert isinstance(now(), datetime)


@pytest.fixture
def tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "setup.cfg").write_text("")
    (tmp_path / "src" / "app.py").write_text("")
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.mark.parametrize(
    ("incomplete", "expected"),
    [
        ("", ["setup.cfg", "src/"]),
        ("s", ["setup.cfg", "src/"]),
        ("sr", ["src/"]),
        ("src/", ["src/app.py"]),
        ("src/a", ["src/app.py"]),
        ("missing/", []),
    ],
)
def test_complete_path(tree: Path, incomplete: str, expected: list[str]) -> None:
    assert complete_path(incomplete) == expected


def test_complete_path_expands_home(monkeypatch: pytest.MonkeyPatch, tree: Path) -> None:
    monkeypatch.setenv("HOME", str(tree))

    assert complete_path("~/se") == ["~/setup.cfg"]
