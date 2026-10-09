import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from typing import Final, cast

from shc.services.errors import ShortcutConfigError
from shc.services.shortcuts.models import (
    MISSING,
    ParamKind,
    ParamSpec,
    ShortcutSpec,
    TyperOptionValue,
)
from shc.services.shortcuts.render import template_placeholders

SHORTCUTS_KEY: Final = "shortcuts"
SHORTCUT_NAME_PATTERN: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
PATH_TYPES: Final = frozenset({"str", "bytes"})

_SHORTCUT_TEXT_FIELDS: Final = ("help", "short_help", "epilog")
_PARAM_TEXT_FIELDS: Final = ("help", "type", "default_factory", "autocompletion", "parser", "flag")
# Fields passed through to `typer.Argument` or `typer.Option`, with their allowed YAML types.
_TYPER_OPTION_FIELDS: Final[Mapping[str, tuple[type, ...]]] = {
    "show_default": (bool, str),
    "show_choices": (bool,),
    "show_envvar": (bool,),
    "hidden": (bool,),
    "envvar": (str,),
    "case_sensitive": (bool,),
    "min": (int, float),
    "max": (int, float),
    "clamp": (bool,),
    "formats": (list,),
    "mode": (str,),
    "encoding": (str,),
    "errors": (str,),
    "lazy": (bool,),
    "atomic": (bool,),
    "exists": (bool,),
    "file_okay": (bool,),
    "dir_okay": (bool,),
    "writable": (bool,),
    "readable": (bool,),
    "resolve_path": (bool,),
    "allow_dash": (bool,),
    "path_type": (str,),
}
_PARAM_KEYS: Final = frozenset(
    {"name", "default", "choices", *_PARAM_TEXT_FIELDS, *_TYPER_OPTION_FIELDS}
)
_SHORTCUT_KEYS: Final = frozenset(
    {"command", "requirements", "arguments", "options", *_SHORTCUT_TEXT_FIELDS}
)


@dataclass(frozen=True, slots=True)
class ParsedShortcuts:
    """Validated shortcuts and non-fatal configuration warnings."""

    shortcuts: dict[str, ShortcutSpec] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()


def parse_shortcuts(
    data: Mapping[str, object], *, reserved: Collection[str] = ()
) -> ParsedShortcuts:
    """Validate a loaded configuration document and build shortcut specs."""
    _check_keys(data, frozenset({SHORTCUTS_KEY}), "configuration")
    entries = data.get(SHORTCUTS_KEY)
    if entries is None:
        entries = {}
    if not isinstance(entries, Mapping):
        raise ShortcutConfigError(f"'{SHORTCUTS_KEY}' must be a mapping of names to shortcuts")

    shortcuts: dict[str, ShortcutSpec] = {}
    warnings: list[str] = []
    for name, entry in entries.items():
        spec = parse_shortcut(str(name), entry, reserved=reserved)
        shortcuts[spec.name] = spec
        warnings.extend(unused_param_warnings(spec))
    return ParsedShortcuts(shortcuts=shortcuts, warnings=tuple(warnings))


def parse_shortcut(name: str, entry: object, *, reserved: Collection[str] = ()) -> ShortcutSpec:
    """Validate one shortcut entry and build its spec."""
    if not SHORTCUT_NAME_PATTERN.fullmatch(name):
        raise ShortcutConfigError(
            f"invalid shortcut name {name!r}: use letters, digits, '-' and '_'"
        )
    if name in reserved:
        raise ShortcutConfigError(f"shortcut name {name!r} is reserved")
    where = f"shortcut {name!r}"
    if not isinstance(entry, Mapping):
        raise ShortcutConfigError(f"{where} must be a mapping")
    _check_keys(entry, _SHORTCUT_KEYS, where)

    command = entry.get("command")
    if not isinstance(command, str) or not command.strip():
        raise ShortcutConfigError(f"{where} requires a non-empty 'command' string")

    spec = ShortcutSpec(
        name=name,
        command=command,
        help=_optional_str(entry, "help", where),
        short_help=_optional_str(entry, "short_help", where),
        epilog=_optional_str(entry, "epilog", where),
        requirements=_str_tuple(entry.get("requirements", []), f"{where} 'requirements'"),
        arguments=_parse_params(entry.get("arguments", []), "argument", where),
        options=_parse_params(entry.get("options", []), "option", where),
    )
    _check_param_names(spec)
    _check_argument_order(spec)
    return spec


def unused_param_warnings(spec: ShortcutSpec) -> list[str]:
    """Report declared parameters that the command template never uses."""
    used = {placeholder.name for placeholder in template_placeholders(spec.command)}
    return [
        f"shortcut {spec.name!r}: {param.kind} {param.name!r} is not used in the command"
        for param in spec.params
        if param.name not in used
    ]


def _parse_params(raw: object, kind: ParamKind, where: str) -> tuple[ParamSpec, ...]:
    if not isinstance(raw, list):
        raise ShortcutConfigError(f"{where} '{kind}s' must be a list")
    return tuple(_parse_param(item, kind, where) for item in raw)


def _parse_param(raw: object, kind: ParamKind, where: str) -> ParamSpec:
    if not isinstance(raw, Mapping):
        raise ShortcutConfigError(f"{where}: each {kind} must be a mapping")
    name = raw.get("name")
    if not isinstance(name, str) or not name.isidentifier():
        raise ShortcutConfigError(f"{where}: {kind} name {name!r} must be a Python identifier")
    where = f"{where} {kind} {name!r}"
    _check_keys(raw, _PARAM_KEYS, where)

    text = {key: _optional_str(raw, key, where) for key in _PARAM_TEXT_FIELDS}
    param = ParamSpec(
        name=name,
        kind=kind,
        help=text["help"],
        type=text["type"] or "str",
        default=_default(raw),
        default_factory=text["default_factory"],
        autocompletion=text["autocompletion"],
        parser=text["parser"],
        choices=_str_tuple(raw["choices"], f"{where} 'choices'") if "choices" in raw else None,
        flag=text["flag"],
        typer_options=_typer_options(raw, where),
    )
    _check_param(param, where)
    return param


def _check_param(param: ParamSpec, where: str) -> None:
    if param.default is not MISSING and param.default_factory is not None:
        raise ShortcutConfigError(f"{where}: 'default' and 'default_factory' are exclusive")
    _check_choices(param, where)
    if param.flag is not None:
        if param.kind == "argument":
            raise ShortcutConfigError(f"{where}: 'flag' is only valid for options")
        if not param.flag.startswith("-") or len(param.flag.split()) != 1:
            raise ShortcutConfigError(f"{where}: 'flag' must be a single word starting with '-'")
    path_type = param.typer_options.get("path_type")
    if path_type is not None and path_type not in PATH_TYPES:
        raise ShortcutConfigError(f"{where}: 'path_type' must be one of {sorted(PATH_TYPES)}")


def _check_choices(param: ParamSpec, where: str) -> None:
    if param.choices is None:
        return
    if not param.choices:
        raise ShortcutConfigError(f"{where}: 'choices' must not be empty")
    if param.default is MISSING or param.default is None:
        return
    defaults = param.default if isinstance(param.default, tuple) else (param.default,)
    if not all(value in param.choices for value in defaults):
        raise ShortcutConfigError(f"{where}: 'default' must be one of the choices")


def _check_argument_order(spec: ShortcutSpec) -> None:
    optional = None
    for argument in spec.arguments:
        if argument.has_default:
            optional = argument
        elif optional is not None:
            raise ShortcutConfigError(
                f"shortcut {spec.name!r}: required argument {argument.name!r} "
                f"cannot follow optional argument {optional.name!r}"
            )


def _check_param_names(spec: ShortcutSpec) -> None:
    seen: set[str] = set()
    for param in spec.params:
        if param.name in seen:
            raise ShortcutConfigError(
                f"shortcut {spec.name!r}: parameter {param.name!r} is declared twice"
            )
        seen.add(param.name)
    for placeholder in template_placeholders(spec.command):
        if placeholder.name not in seen:
            raise ShortcutConfigError(
                f"shortcut {spec.name!r}: placeholder {{{placeholder.name}}} "
                "has no matching argument or option"
            )


def _typer_options(raw: Mapping[str, object], where: str) -> dict[str, TyperOptionValue]:
    options: dict[str, TyperOptionValue] = {}
    for key, allowed in _TYPER_OPTION_FIELDS.items():
        if key not in raw:
            continue
        value = raw[key]
        if list in allowed:
            options[key] = _str_tuple(value, f"{where} {key!r}")
        elif _is_instance(value, allowed):
            options[key] = cast(TyperOptionValue, value)
        else:
            expected = " or ".join(kind.__name__ for kind in allowed)
            raise ShortcutConfigError(f"{where}: {key!r} must be {expected}")
    return options


def _default(raw: Mapping[str, object]) -> object:
    if "default" not in raw:
        return MISSING
    value = raw["default"]
    return tuple(value) if isinstance(value, list) else value


def _is_instance(value: object, allowed: tuple[type, ...]) -> bool:
    # YAML booleans are ints in Python; accept them only where bool is allowed.
    if isinstance(value, bool):
        return bool in allowed
    return isinstance(value, allowed)


def _optional_str(raw: Mapping[str, object], key: str, where: str) -> str | None:
    value = raw.get(key)
    if value is not None and not isinstance(value, str):
        raise ShortcutConfigError(f"{where}: {key!r} must be a string")
    return value


def _str_tuple(value: object, where: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ShortcutConfigError(f"{where} must be a list of strings")
    return tuple(cast(list[str], value))


def _check_keys(raw: Mapping[str, object], allowed: frozenset[str], where: str) -> None:
    unknown = sorted(str(key) for key in raw if key not in allowed)
    if unknown:
        raise ShortcutConfigError(f"{where}: unknown keys {', '.join(unknown)}")
