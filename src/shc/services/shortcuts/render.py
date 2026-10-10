import shlex
import string
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from shc.services.errors import ShortcutConfigError
from shc.services.shortcuts.models import ParamSpec, ShortcutSpec

RAW_CONVERSION = "r"


@dataclass(frozen=True, slots=True)
class Placeholder:
    """A `{name}` or `{name!r}` field in a command template."""

    name: str
    raw: bool


def template_placeholders(command: str) -> tuple[Placeholder, ...]:
    """Return the placeholders of a command template in order of appearance."""
    try:
        fields = list(string.Formatter().parse(command))
    except ValueError as error:
        raise ShortcutConfigError(f"invalid command template {command!r}: {error}") from error

    placeholders = []
    for _, name, format_spec, conversion in fields:
        if name is None:
            continue
        if not name.isidentifier():
            raise ShortcutConfigError(
                f"invalid placeholder {{{name}}} in {command!r}: use a parameter name"
            )
        if format_spec:
            raise ShortcutConfigError(
                f"format specs are not supported in placeholder {{{name}:{format_spec}}}"
            )
        if conversion not in {None, RAW_CONVERSION}:
            raise ShortcutConfigError(
                f"unknown conversion !{conversion} in placeholder {{{name}}}; only !r is supported"
            )
        placeholders.append(Placeholder(name=name, raw=conversion == RAW_CONVERSION))
    return tuple(placeholders)


def render_command(spec: ShortcutSpec, values: Mapping[str, object]) -> str:
    """Substitute parameter values into the shortcut's command template."""
    text = ""
    after_empty_value = False
    for literal, name, _, conversion in string.Formatter().parse(spec.command):
        # An empty value between two spaces would leave a double space; keep one.
        skip = int(after_empty_value and text.endswith(" ") and literal.startswith(" "))
        text += literal[skip:]
        after_empty_value = False
        if name is not None:
            rendered = render_value(
                spec.param(name), values[name], raw=conversion == RAW_CONVERSION
            )
            text += rendered
            after_empty_value = not rendered
    return text.strip()


def render_value(param: ParamSpec, value: object, *, raw: bool = False) -> str:
    """Render one parameter value as shell text."""
    if value is None or value is False:
        return ""
    if value is True:
        return param.flag or "--" + param.name.replace("_", "-")
    if isinstance(value, list | tuple):
        return " ".join(
            rendered for item in value if (rendered := render_value(param, item, raw=raw))
        )
    text = value.isoformat() if isinstance(value, date) else str(value)
    if not raw:
        text = shlex.quote(text)
    return f"{param.flag} {text}" if param.flag else text
