from datetime import datetime
from pathlib import Path
from types import GenericAlias, UnionType
from typing import Final
from uuid import UUID

from typer import FileBinaryRead, FileText

from shc.services.errors import ShortcutConfigError

type Annotation = type | GenericAlias | UnionType

BASE_TYPES: Final[dict[str, type]] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "Path": Path,
    "datetime": datetime,
    "UUID": UUID,
    "FileText": FileText,
    "FileBinaryRead": FileBinaryRead,
}
_LIST_PREFIXES: Final = ("list[", "List[")
_TUPLE_PREFIXES: Final = ("tuple[", "Tuple[")
_OPTIONAL_PREFIX: Final = "Optional["


def parse_type(text: str) -> Annotation:
    """Translate a type string from the configuration into a type Typer supports.

    Accepted forms: a name from `BASE_TYPES`, `list[T]`, `tuple[T1, T2, ...]`,
    `Optional[T]`, and `T | None`. Names are looked up, never evaluated.
    """
    text = text.strip()
    optional, inner = _strip_optional(text)
    annotation = _parse_required(inner, text)
    return annotation | None if optional else annotation


def is_bool(annotation: object) -> bool:
    """Whether the annotation is `bool` or `bool | None`."""
    return annotation in {bool, bool | None}


def _strip_optional(text: str) -> tuple[bool, str]:
    if text.startswith(_OPTIONAL_PREFIX) and text.endswith("]"):
        return True, text[len(_OPTIONAL_PREFIX) : -1].strip()
    members = _split(text, "|")
    if len(members) == 1:
        return False, text
    others = [member for member in members if member != "None"]
    if len(others) != 1 or len(members) - len(others) != 1:
        raise ShortcutConfigError(f"unsupported type {text!r}: only unions with None are supported")
    return True, others[0]


def _parse_required(text: str, original: str) -> type | GenericAlias:
    if text in BASE_TYPES:
        return BASE_TYPES[text]
    for prefix in _LIST_PREFIXES:
        if text.startswith(prefix) and text.endswith("]"):
            item = _parse_base(text[len(prefix) : -1].strip(), original)
            return GenericAlias(list, (item,))
    for prefix in _TUPLE_PREFIXES:
        if text.startswith(prefix) and text.endswith("]"):
            items = tuple(
                _parse_base(item, original) for item in _split(text[len(prefix) : -1], ",")
            )
            return GenericAlias(tuple, items)
    raise ShortcutConfigError(
        f"unsupported type {original!r}; use one of {', '.join(BASE_TYPES)}, "
        "list[T], tuple[T1, T2], Optional[T] or T | None"
    )


def _parse_base(text: str, original: str) -> type:
    if text not in BASE_TYPES:
        raise ShortcutConfigError(
            f"unsupported item type {text!r} in {original!r}; use one of {', '.join(BASE_TYPES)}"
        )
    return BASE_TYPES[text]


def _split(text: str, separator: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for char in text:
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
        if char == separator and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    parts.append("".join(current).strip())
    return parts
