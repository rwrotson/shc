from dataclasses import dataclass, field
from os import getenv
from pathlib import Path
from rich import print
from typing import Any, Callable

from click import Context, Parameter, ParamType
from click.shell_completion import CompletionItem
from yaml import safe_load, YAMLError


CONFIG_PATH = Path(getenv("SHC_CONFIG_PATH", default="~/.shc-config.yml")).expanduser()

type _ShellCompleteCallable = Callable[[Context, Parameter, str], list[CompletionItem] | list[str]]

# always parse as string
# because it just passes string values to inner script
# inner script will take care of all the else ?


@dataclass(slots=True, frozen=True)
class _ParamConfig[T: type]:
    name: str
    help: str
    type: T = str
    # Params
    default: Any | None = ...
    default_factory: Callable[[], Any] | None = None  # TODO
    shell_complete: _ShellCompleteCallable | None = None  # TODO
    autocompletion: Callable[..., Any] | None = None  # TODO
    # Custom type
    parser: Callable[[str], T] | None = None  # TODO
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
    path_type: type[str] | type[bytes] | None = None


@dataclass(slots=True, frozen=True)
class _CommandConfig:
    name: str
    command: str
    help: str
    epilog: str | None = None
    short_help: str | None = None
    requirements: list[str] = field(default_factory=list, init=False)
    arguments: list[_ParamConfig] = field(default_factory=list)
    options: list[_ParamConfig] = field(default_factory=list)

    def __post_init__(self):
        # Convert string factory names to actual callables
        factory = DEFAULT_FACTORIES.get(self._default_factory, None)
        if self._default_factory and factory is None:
            raise ValueError(f"Invalid default_factory: {self._default_factory}")

        # Assign resolved callable to default_factory
        object.__setattr__(self, "default_factory", factory)