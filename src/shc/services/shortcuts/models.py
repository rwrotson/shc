from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Final, Literal

type ParamKind = Literal["argument", "option"]
type TyperOptionValue = bool | int | float | str | tuple[str, ...]


class Missing(Enum):
    """Marker for a parameter without a default value."""

    MISSING = "MISSING"


MISSING: Final = Missing.MISSING


@dataclass(frozen=True, slots=True)
class ParamSpec:
    """Declaration of one shortcut argument or option."""

    name: str
    kind: ParamKind
    help: str | None = None
    type: str = "str"
    default: object = MISSING
    default_factory: str | None = None
    autocompletion: str | None = None
    parser: str | None = None
    choices: tuple[str, ...] | None = None
    flag: str | None = None
    # Keyword arguments passed unchanged to `typer.Argument` or `typer.Option`.
    typer_options: Mapping[str, TyperOptionValue] = field(default_factory=dict)

    @property
    def has_default(self) -> bool:
        """Whether a default value or factory is declared."""
        return self.default is not MISSING or self.default_factory is not None


@dataclass(frozen=True, slots=True)
class ShortcutSpec:
    """Declaration of one shortcut command."""

    name: str
    command: str
    help: str | None = None
    short_help: str | None = None
    epilog: str | None = None
    requirements: tuple[str, ...] = ()
    arguments: tuple[ParamSpec, ...] = ()
    options: tuple[ParamSpec, ...] = ()

    @property
    def params(self) -> tuple[ParamSpec, ...]:
        """Arguments followed by options."""
        return self.arguments + self.options

    def param(self, name: str) -> ParamSpec:
        """Return the parameter with the given name."""
        for param in self.params:
            if param.name == name:
                return param
        raise KeyError(name)
