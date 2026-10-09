import json
import os
import subprocess
import sys
from collections.abc import Callable
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console
from typer.testing import CliRunner

import shc.cli.app as app_module
from shc.cli.app import app
from shc.cli.shortcuts.loading import RESERVED_NAMES

runner = CliRunner()

SHORTCUTS = """\
shortcuts:
  say:
    command: echo {words}
    help: Print words
    arguments:
      - name: words
        type: list[str]
"""


def test_version_output_contains_app_name() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "shc" in result.output


@pytest.mark.parametrize("flag", ["--authors", "-A"])
def test_authors_flag_shows_author_name(flag: str) -> None:
    result = runner.invoke(app, [flag])
    assert result.exit_code == 0
    assert "Igor Lashkov" in result.output


def test_no_arguments_shows_help() -> None:
    result = runner.invoke(app, [])
    assert "Run saved shortcuts for shell commands." in result.output


def test_reserved_names_match_built_in_groups() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for name in RESERVED_NAMES:
        assert name in result.output


@pytest.mark.parametrize("flag", ["--dry-run", "-n"])
def test_dry_run_prints_command(write_shortcuts: Callable[[str], Path], flag: str) -> None:
    write_shortcuts(SHORTCUTS)

    result = runner.invoke(app, [flag, "say", "hello world", "[red]x[/red]"])

    assert result.exit_code == 0
    assert result.stdout == "echo 'hello world' '[red]x[/red]'\n"


def test_dry_run_json_output(write_shortcuts: Callable[[str], Path]) -> None:
    write_shortcuts(SHORTCUTS)

    result = runner.invoke(app, ["--output-format", "json", "-n", "say", "hi"])

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"command": "echo hi"}


@pytest.mark.parametrize("flag", ["--verbose", "-V"])
def test_verbose_flag_exits_zero(write_shortcuts: Callable[[str], Path], flag: str) -> None:
    write_shortcuts(SHORTCUTS)
    result = runner.invoke(app, [flag, "-n", "say", "hi"])
    assert result.exit_code == 0


def test_command_uses_console_at_invocation(monkeypatch: pytest.MonkeyPatch) -> None:
    output = StringIO()
    console = Console(file=output, force_terminal=False)
    monkeypatch.setattr(app_module, "get_console", lambda: console)

    result = runner.invoke(app, ["config", "list"])

    assert result.exit_code == 0
    assert "Name" in output.getvalue()


def test_output_format_invalid_value_fails() -> None:
    result = runner.invoke(app, ["--output-format", "xml", "config", "list"])
    assert result.exit_code != 0


def main_env(tmp_path: Path) -> dict[str, str]:
    shortcuts = tmp_path / "s.yml"
    shortcuts.write_text(SHORTCUTS)
    return {
        **os.environ,
        "SHC_LOG__DIR": str(tmp_path / "logs"),
        "SHC_SHORTCUTS__FILE": str(shortcuts),
        "SHC_SHORTCUTS__PLUGINS_DIR": str(tmp_path / "plugins"),
    }


def test_json_stdout_stays_clean_with_verbose_logging(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from shc.main import main; main()",
            "--verbose",
            "--output-format",
            "json",
            "-n",
            "say",
            "hello",
        ],
        capture_output=True,
        text=True,
        env=main_env(tmp_path),
        check=False,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout) == {"command": "echo hello"}
    assert "running shortcut" in result.stderr


def test_shortcut_runs_in_shell(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-c", "from shc.main import main; main()", "say", "hello", "world"],
        capture_output=True,
        text=True,
        env=main_env(tmp_path),
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == "hello world\n"
