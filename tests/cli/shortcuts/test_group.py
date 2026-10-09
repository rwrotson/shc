import json
from collections.abc import Callable
from pathlib import Path

import pytest
from structlog.testing import capture_logs
from typer.testing import CliRunner

from shc.cli.app import app

runner = CliRunner()

GOOD_AND_BROKEN = """\
shortcuts:
  say:
    command: echo {word}
    short_help: Say a word
    arguments:
      - name: word
        autocompletion: words
  bad:
    command: echo {n}
    arguments:
      - name: n
        type: dict
"""

WORDS_PLUGIN = """\
from shc import plugin


@plugin.autocompletion("words")
def words(incomplete: str) -> list[str]:
    return [word for word in ("hello", "help") if word.startswith(incomplete)]
"""


@pytest.fixture
def configured(
    write_shortcuts: Callable[[str], Path], write_plugin: Callable[[str, str], Path]
) -> None:
    write_shortcuts(GOOD_AND_BROKEN)
    write_plugin("words", WORDS_PLUGIN)


def test_help_lists_shortcuts_and_skips_broken(
    configured: None,
) -> None:
    with capture_logs() as logs:
        result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "say" in result.stdout
    assert "Say a word" in result.stdout
    assert " bad " not in result.stdout
    assert {"event": "shortcut skipped", "shortcut": "bad"}.items() <= logs[0].items()


def test_broken_shortcut_reports_its_error(configured: None) -> None:
    result = runner.invoke(app, ["bad", "x"])

    assert result.exit_code == 2
    assert result.stderr.startswith("Error: unsupported type 'dict'")


def test_resolution_errors_respect_json_output(configured: None) -> None:
    result = runner.invoke(app, ["-f", "json", "bad", "x"])

    assert result.exit_code == 2
    assert result.stdout == ""
    assert json.loads(result.stderr)["error"]["type"] == "ShortcutConfigError"


def test_unknown_command_is_a_usage_error(configured: None) -> None:
    result = runner.invoke(app, ["nope"])

    assert result.exit_code == 2
    assert "No such command" in result.output


def test_plugin_completion(configured: None) -> None:
    result = runner.invoke(
        app,
        [],
        env={"_SHC_COMPLETE": "complete_zsh", "_TYPER_COMPLETE_ARGS": "shc say hel"},
        prog_name="shc",
    )

    assert '"hello"' in result.stdout
    assert '"help"' in result.stdout


def test_missing_file_still_lists_built_in_groups() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "config" in result.stdout
    assert result.stderr == ""


def test_invalid_file_keeps_built_in_groups_working(write_shortcuts: Callable[[str], Path]) -> None:
    write_shortcuts("shortcuts: [")

    with capture_logs() as logs:
        help_result = runner.invoke(app, ["--help"])
    path_result = runner.invoke(app, ["config", "path"])
    run_result = runner.invoke(app, ["anything"])

    assert help_result.exit_code == 0
    assert logs[0]["event"] == "shortcuts are unavailable"
    assert path_result.exit_code == 0
    assert run_result.exit_code == 2
    assert "invalid YAML" in run_result.stderr


def test_reserved_name_in_file_disables_shortcuts(write_shortcuts: Callable[[str], Path]) -> None:
    write_shortcuts("shortcuts:\n  config:\n    command: echo\n")

    with capture_logs() as logs:
        result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "'config' is reserved" in logs[0]["error"]
