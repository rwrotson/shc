from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from click import ParamType
from rich import print
from yaml import YAMLError, safe_load

from src.consts import CONFIG_PATH
from src.parser import (
    parse_autocompletion_callable,
    parse_default_factory_callable,
    parse_parser_callable,
    parse_path_type,
    parse_shell_complete_callable,
    parse_typer_type,
)
from src.types import (
    AutocompletionCallable,
    DefaultFactoryCallable,
    ParserCallable,
    ShellCompleteCallable,
)


@dataclass(slots=True, frozen=True)
class _ParamConfig:
    name: str
    help: str | None = None
    type: type = field(default=str, metadata={"parser": parse_typer_type})
    # Params
    default: Any | None = ...
    default_factory: DefaultFactoryCallable | None = field(
        default=None,
        metadata={"parser": parse_default_factory_callable},
    )
    shell_complete: ShellCompleteCallable | None = field(
        default=None,
        metadata={"parser": parse_shell_complete_callable},
    )
    autocompletion: AutocompletionCallable | None = field(
        default=None,
        metadata={"parser": parse_autocompletion_callable},
    )
    # Custom type
    parser: ParserCallable | None = field(
        default=None,
        metadata={"parser": parse_parser_callable},
    )
    click_type: ParamType | None = None
    # TyperArgument
    show_default: bool | str = True
    show_choices: bool = True
    show_envvar: bool = True
    hidden: bool = False
    # Choice
    case_sensitive: bool = True
    # Numbers
    min: int | float | None = None
    max: int | float | None = None
    clamp: bool = False
    # DateTime
    formats: list[str] | None = None
    # File
    mode: str | None = None
    encoding: str | None = None
    errors: str | None = "strict"
    lazy: bool | None = None
    atomic: bool = False
    # Path
    exists: bool = False
    file_okay: bool = True
    dir_okay: bool = True
    writable: bool = False
    readable: bool = True
    resolve_path: bool = False
    allow_dash: bool = False
    path_type: type | None = field(default=None, metadata={"parser": parse_path_type})


@dataclass(slots=True, frozen=True)
class _CommandConfig:
    name: str
    command: str | Path
    help: str | None = None
    epilog: str | None = None
    short_help: str | None = None
    requirements: list[str] = field(default_factory=list)
    arguments: list[_ParamConfig] = field(default_factory=list)
    options: list[_ParamConfig] = field(default_factory=list)


def _read_yaml_file(file_path: Path) -> dict:
    if not file_path.exists():
        raise FileNotFoundError(f"File not found at {file_path}")

    try:
        with (file_path.open() as f):
            return safe_load(f)
    except YAMLError as e:
        raise ValueError(f"Error parsing yaml file {file_path}") from e


def _parse_config_file(config_path: Path) -> list[_CommandConfig]:
    config_dict = _read_yaml_file(config_path)

    try:
        commands_dict = config_dict["commands"]
    except KeyError:
        raise ValueError("Missing 'commands' key in config file")

    if not isinstance(commands_dict, dict):
        raise ValueError("Expected 'commands' key to be a dictionary")

    for command_name, command_config in commands_dict.items():
        command_config["name"] = command_name
        command_config["arguments"] = [
            _ParamConfig(**arg) for arg in command_config.get("arguments", [])
        ]
        command_config["options"] = [
            _ParamConfig(**opt) for opt in command_config.get("options", [])
        ]

    print(commands_dict)

    return [_CommandConfig(**cmd) for cmd in config_dict.values()]


a = _parse_config_file(CONFIG_PATH)

print(a)