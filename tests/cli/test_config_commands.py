import json
import os
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner

from shc.cli.app import app

runner = CliRunner()

SHORTCUTS = """\
# personal shortcuts
shortcuts:
  gco:
    command: git checkout {branch}
    help: Checkout a branch
    short_help: Checkout
    arguments:
      - name: branch
  up:
    command: cd ..  # parent
"""


def test_list_text_and_json(write_shortcuts: Callable[[str], Path]) -> None:
    write_shortcuts(SHORTCUTS)

    text = runner.invoke(app, ["config", "list"])
    data = runner.invoke(app, ["-f", "json", "config", "list"])

    assert text.exit_code == 0
    assert "Checkout" in text.stdout
    assert "cd .." in text.stdout
    assert json.loads(data.stdout) == [
        {"name": "gco", "help": "Checkout", "command": "git checkout {branch}"},
        {"name": "up", "help": None, "command": "cd .."},
    ]


def test_list_with_missing_file_is_empty() -> None:
    result = runner.invoke(app, ["-f", "json", "config", "list"])

    assert result.exit_code == 0
    assert json.loads(result.stdout) == []


def test_show_text_and_json(write_shortcuts: Callable[[str], Path]) -> None:
    write_shortcuts(SHORTCUTS)

    text = runner.invoke(app, ["config", "show", "up"])
    data = runner.invoke(app, ["-f", "json", "config", "show", "gco"])
    missing = runner.invoke(app, ["config", "show", "nope"])

    assert text.stdout == "up:\n  command: cd ..\n"
    assert json.loads(data.stdout)["arguments"] == [{"name": "branch"}]
    assert missing.exit_code == 1
    assert missing.stderr == "Error: shortcut 'nope' is not defined\n"


def test_add_then_run_and_remove(config_dir: Path) -> None:
    added = runner.invoke(
        app, ["config", "add", "hi", "echo hello {who}", "-d", "Greet", "-r", "echo"]
    )
    dry = runner.invoke(app, ["-n", "hi", "big world"])
    duplicate = runner.invoke(app, ["config", "add", "hi", "echo"])
    replaced = runner.invoke(app, ["-f", "json", "config", "add", "hi", "echo {a}", "--force"])
    removed = runner.invoke(app, ["config", "remove", "hi"])

    assert added.exit_code == 0
    assert "Added shortcut hi" in added.stdout
    assert dry.stdout == "echo hello 'big world'\n"
    assert duplicate.exit_code == 1
    assert "--force" in duplicate.stderr
    assert json.loads(replaced.stdout) == {"name": "hi", "arguments": ["a"]}
    assert removed.exit_code == 0
    assert "Removed shortcut hi" in removed.stdout
    assert (config_dir / "shortcuts.yml").read_text() == "shortcuts: {}\n"


def test_add_rejects_reserved_names() -> None:
    result = runner.invoke(app, ["config", "add", "completion", "echo"])

    assert result.exit_code == 2
    assert "reserved" in result.stderr


def test_add_and_remove_keep_comments(write_shortcuts: Callable[[str], Path]) -> None:
    path = write_shortcuts(SHORTCUTS)

    runner.invoke(app, ["config", "add", "ls2", "ls -la"])
    runner.invoke(app, ["-f", "json", "config", "remove", "ls2"])

    assert path.read_text() == SHORTCUTS


def test_remove_missing_shortcut_fails() -> None:
    result = runner.invoke(app, ["-f", "json", "config", "remove", "nope"])

    assert result.exit_code == 1
    assert json.loads(result.stderr)["error"]["type"] == "ShortcutNotFoundError"


def test_validate_reports_count_warnings_and_json(write_shortcuts: Callable[[str], Path]) -> None:
    path = write_shortcuts(
        SHORTCUTS + "  quiet:\n    command: echo\n    options:\n      - name: loud\n"
    )

    text = runner.invoke(app, ["config", "validate"])
    data = runner.invoke(app, ["-f", "json", "config", "validate"])

    assert text.exit_code == 0
    assert "Warning: shortcut 'quiet': option 'loud' is not used" in text.stdout
    assert "3 shortcuts valid" in text.stdout
    assert json.loads(data.stdout) == {
        "file": str(path),
        "shortcuts": ["gco", "quiet", "up"],
        "warnings": ["shortcut 'quiet': option 'loud' is not used in the command"],
    }


def test_validate_singular_message(write_shortcuts: Callable[[str], Path]) -> None:
    write_shortcuts("shortcuts:\n  up:\n    command: cd ..\n")

    assert "1 shortcut valid" in runner.invoke(app, ["config", "validate"]).stdout


def test_validate_reports_build_and_plugin_errors(write_shortcuts: Callable[[str], Path]) -> None:
    write_shortcuts(
        "shortcuts:\n"
        "  a:\n    command: x {n}\n    arguments:\n      - name: n\n        type: dict\n"
        "  b:\n    command: x {n}\n    arguments:\n      - name: n\n        type: set\n"
    )
    build_errors = runner.invoke(app, ["config", "validate"])
    write_shortcuts(
        "shortcuts:\n  a:\n    command: x {n}\n    arguments:\n"
        "      - name: n\n        autocompletion: nope\n"
    )
    plugin_errors = runner.invoke(app, ["config", "validate"])

    assert build_errors.exit_code == 2
    assert "shortcut 'a': unsupported type 'dict'" in build_errors.stderr
    assert "shortcut 'b': unsupported type 'set'" in build_errors.stderr
    assert plugin_errors.exit_code == 2
    assert "unknown autocompletion plugin 'nope'" in plugin_errors.stderr


def test_path_text_and_json(config_dir: Path) -> None:
    text = runner.invoke(app, ["config", "path"])
    data = runner.invoke(app, ["-f", "json", "config", "path"])

    assert text.stdout == f"{config_dir / 'shortcuts.yml'}\n{config_dir / 'plugins'}\n"
    assert json.loads(data.stdout) == {
        "file": str(config_dir / "shortcuts.yml"),
        "plugins_dir": str(config_dir / "plugins"),
    }


def editor(tmp_path: Path, content: str) -> str:
    script = tmp_path / "editor.py"
    script.write_text(f"import pathlib, sys\npathlib.Path(sys.argv[1]).write_text({content!r})\n")
    return f"{sys.executable} {script}"


def test_edit_creates_file_runs_editor_and_validates(
    monkeypatch: pytest.MonkeyPatch, config_dir: Path, tmp_path: Path
) -> None:
    content = "shortcuts:\n  up:\n    command: cd ..\n"
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.setenv("EDITOR", editor(tmp_path, content))

    result = runner.invoke(app, ["config", "edit"])

    assert result.exit_code == 0, result.output
    assert "1 shortcut valid" in result.stdout
    assert (config_dir / "shortcuts.yml").read_text() == content


def test_edit_reports_invalid_result(
    monkeypatch: pytest.MonkeyPatch, write_shortcuts: Callable[[str], Path], tmp_path: Path
) -> None:
    write_shortcuts(SHORTCUTS)
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.setenv("EDITOR", editor(tmp_path, "shortcuts: [broken\n"))

    result = runner.invoke(app, ["config", "edit"])

    assert result.exit_code == 2
    assert "invalid YAML" in result.stderr


def test_edit_prefers_visual_and_propagates_editor_failure(
    monkeypatch: pytest.MonkeyPatch, write_shortcuts: Callable[[str], Path]
) -> None:
    path = write_shortcuts(SHORTCUTS)
    monkeypatch.setenv("VISUAL", f"{sys.executable} -c 'raise SystemExit(3)'")
    monkeypatch.setenv("EDITOR", "should-not-run")

    result = runner.invoke(app, ["config", "edit"])

    assert result.exit_code == 3
    assert path.read_text() == SHORTCUTS
    assert "EDITOR" in os.environ
