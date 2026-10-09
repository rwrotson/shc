import io
import json
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import pytest
from rich.console import Console

from shc.cli.context import AppContext
from shc.cli.shortcuts.builder import build_command, plain_value
from shc.config import Settings
from shc.services.errors import PluginError, ShortcutConfigError
from shc.services.plugins.registry import Registry, builtin_registry
from shc.services.shortcuts.parsing import parse_shortcut
from shc.utils.output import OutputFormat


@dataclass(frozen=True)
class Result:
    exit_code: int
    stdout: str


@pytest.fixture
def run(capsys: pytest.CaptureFixture[str]) -> Callable[..., Result]:
    def invoke(
        entry: dict[str, object],
        args: list[str],
        *,
        registry: Registry | None = None,
        output_format: OutputFormat = OutputFormat.json,
        dry_run: bool = True,
    ) -> Result:
        command = build_command(parse_shortcut("s", entry), registry or builtin_registry())
        obj = AppContext(
            settings=Settings(), console=Console(), output_format=output_format, dry_run=dry_run
        )
        capsys.readouterr()
        with pytest.raises(SystemExit) as exit_info:
            command.main(args, prog_name="s", obj=obj)
        code = exit_info.value.code
        return Result(
            exit_code=code if isinstance(code, int) else 1, stdout=capsys.readouterr().out
        )

    return invoke


def rendered(result: Result) -> str:
    assert result.exit_code == 0, result.stdout
    command: str = json.loads(result.stdout)["command"]
    return command


def test_typed_arguments_and_options(run: Callable[..., Result]) -> None:
    entry = {
        "command": "x {count} {names} {pair} {verbose} {level}",
        "arguments": [{"name": "count", "type": "int", "min": 1}],
        "options": [
            {"name": "names", "type": "list[str]", "flag": "--name"},
            {"name": "pair", "type": "tuple[str, int]"},
            {"name": "verbose", "type": "bool"},
            {"name": "level", "type": "float", "default": 0.5, "flag": "-l"},
        ],
    }

    result = run(entry, ["3", "--names", "a b", "--names", "c", "--pair", "k", "2", "--verbose"])

    assert rendered(result) == "x 3 --name 'a b' --name c k 2 --verbose -l 0.5"


def test_type_validation_and_ranges_come_from_typer(run: Callable[..., Result]) -> None:
    entry = {"command": "x {count}", "arguments": [{"name": "count", "type": "int", "min": 1}]}

    assert run(entry, ["0"]).exit_code == 2
    assert run(entry, ["many"]).exit_code == 2


def test_optional_values_render_empty(run: Callable[..., Result]) -> None:
    entry = {
        "command": "x {when} {tag}",
        "options": [{"name": "when", "type": "datetime"}, {"name": "tag"}],
    }

    assert rendered(run(entry, [])) == "x"


def test_optional_argument_default(run: Callable[..., Result]) -> None:
    entry = {"command": "x {name}", "arguments": [{"name": "name", "default": "world"}]}

    assert rendered(run(entry, [])) == "x world"


def test_required_argument_is_enforced(run: Callable[..., Result]) -> None:
    entry = {"command": "x {name}", "arguments": [{"name": "name"}]}

    assert run(entry, []).exit_code == 2


def test_choices_are_case_insensitive_when_configured(run: Callable[..., Result]) -> None:
    entry = {
        "command": "x {mode} {tags}",
        "options": [
            {"name": "mode", "choices": ["soft", "hard"], "case_sensitive": False},
            {"name": "tags", "type": "list[str]", "choices": ["a", "b"], "default": ["a"]},
        ],
    }

    assert rendered(run(entry, ["--mode", "HARD"])) == "x hard a"
    assert run(entry, ["--mode", "medium"]).exit_code == 2


def test_choices_default_and_optional_types(run: Callable[..., Result]) -> None:
    entry = {
        "command": "x {mode} {extra}",
        "arguments": [{"name": "mode", "choices": ["a", "b"], "default": "b"}],
        "options": [{"name": "extra", "type": "Optional[str]", "choices": ["c"]}],
    }

    assert rendered(run(entry, [])) == "x b"


def test_choices_require_string_types() -> None:
    entry = {"command": "x {n}", "arguments": [{"name": "n", "type": "int", "choices": ["1"]}]}

    with pytest.raises(ShortcutConfigError, match="requires type str or list"):
        build_command(parse_shortcut("s", entry), builtin_registry())


def test_default_factory_from_registry(run: Callable[..., Result]) -> None:
    entry = {
        "command": "x {where}",
        "arguments": [{"name": "where", "type": "Path", "default_factory": "cwd"}],
    }

    assert rendered(run(entry, [])) == f"x {Path.cwd()}"
    help_text = run(entry, ["--help"], output_format=OutputFormat.text).stdout
    assert "cwd()" in help_text


def test_parser_and_path_type_from_configuration(run: Callable[..., Result]) -> None:
    registry = builtin_registry()
    registry.register("parser", "upper", str.upper)
    entry = {
        "command": "x {name} {file}",
        "arguments": [{"name": "name", "parser": "upper"}],
        "options": [{"name": "file", "type": "Path", "path_type": "str"}],
    }

    assert rendered(run(entry, ["abc", "--file", "f"], registry=registry)) == "x ABC f"


def test_unknown_plugin_fails_to_build() -> None:
    entry = {"command": "x {a}", "arguments": [{"name": "a", "autocompletion": "nope"}]}

    with pytest.raises(PluginError, match="unknown autocompletion plugin 'nope'"):
        build_command(parse_shortcut("s", entry), builtin_registry())


def test_command_metadata() -> None:
    entry = {"command": "x", "help": "Long help", "short_help": "Short", "epilog": "Bye"}

    command = build_command(parse_shortcut("s", entry), builtin_registry())

    assert (command.name, command.help, command.short_help, command.epilog) == (
        "s",
        "Long help",
        "Short",
        "Bye",
    )


def test_text_dry_run_echoes_command(run: Callable[..., Result]) -> None:
    result = run({"command": "echo hi"}, [], output_format=OutputFormat.text)

    assert result.stdout == "echo hi\n"


def test_failed_command_exits_with_its_code(run: Callable[..., Result]) -> None:
    assert run({"command": "exit 4"}, [], dry_run=False).exit_code == 4
    assert run({"command": "true"}, [], dry_run=False).exit_code == 0


class Color(StrEnum):
    red = "red"


def test_plain_value() -> None:
    stream = io.StringIO()
    named = io.BytesIO()
    named.name = "data.bin"

    assert plain_value(Color.red) == "red"
    assert plain_value([Color.red, (1,)]) == ["red", [1]]
    assert plain_value(named) == "data.bin"
    assert plain_value(stream) == str(stream)
    assert plain_value(3) == 3
