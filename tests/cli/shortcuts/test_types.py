from datetime import datetime
from pathlib import Path
from uuid import UUID

import pytest
from typer import FileBinaryRead, FileText

from shc.cli.shortcuts.types import is_bool, parse_type
from shc.services.errors import ShortcutConfigError


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("int", int),
        (" float ", float),
        ("bool", bool),
        ("Path", Path),
        ("datetime", datetime),
        ("UUID", UUID),
        ("FileText", FileText),
        ("FileBinaryRead | None", FileBinaryRead | None),
        ("Optional[str]", str | None),
        ("None | Path", Path | None),
        ("list[int]", list[int]),
        ("List[bool]", list[bool]),
        ("tuple[str, int]", tuple[str, int]),
        ("Tuple[str,int]", tuple[str, int]),
        ("Optional[list[int]]", list[int] | None),
        ("tuple[str, int] | None", tuple[str, int] | None),
    ],
)
def test_parse_type(text: str, expected: object) -> None:
    assert parse_type(text) == expected


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("str | float | bool", "only unions with None"),
        ("None | None", "only unions with None"),
        ("Union[str, int]", "unsupported type"),
        ("dict", "unsupported type"),
        ("os.system", "unsupported type"),
        ("list[list[int]]", r"unsupported item type 'list\[int\]'"),
        ("tuple[str, dict]", "unsupported item type 'dict'"),
    ],
)
def test_parse_type_rejects_unsupported(text: str, message: str) -> None:
    with pytest.raises(ShortcutConfigError, match=message):
        parse_type(text)


def test_is_bool() -> None:
    assert is_bool(bool)
    assert is_bool(bool | None)
    assert not is_bool(int)
