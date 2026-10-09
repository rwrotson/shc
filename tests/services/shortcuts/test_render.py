from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from shc.services.errors import ShortcutConfigError
from shc.services.shortcuts.models import ParamSpec, ShortcutSpec
from shc.services.shortcuts.render import (
    Placeholder,
    render_command,
    render_value,
    template_placeholders,
)

ARG = ParamSpec(name="value", kind="argument")
FLAGGED = ParamSpec(name="sort_by", kind="option", flag="--sort")
UNFLAGGED = ParamSpec(name="dry_run", kind="option")


def test_template_placeholders_in_order() -> None:
    assert template_placeholders("cp {src} {dst!r} {{literal}}") == (
        Placeholder(name="src", raw=False),
        Placeholder(name="dst", raw=True),
    )


@pytest.mark.parametrize(
    ("command", "message"),
    [
        ("echo {", "invalid command template"),
        ("echo {a.b}", "use a parameter name"),
        ("echo {}", "use a parameter name"),
        ("echo {a:>5}", "format specs"),
        ("echo {a!s}", "only !r"),
    ],
)
def test_template_placeholders_rejects_invalid_fields(command: str, message: str) -> None:
    with pytest.raises(ShortcutConfigError, match=message):
        template_placeholders(command)


@pytest.mark.parametrize(
    ("param", "value", "expected"),
    [
        (ARG, "my file.txt", "'my file.txt'"),
        (ARG, 3, "3"),
        (ARG, Path("dir/a b"), "'dir/a b'"),
        (ARG, date(2026, 10, 9), "2026-10-09"),
        (ARG, datetime(2026, 10, 9, 8, 30, tzinfo=UTC), "2026-10-09T08:30:00+00:00"),
        (ARG, None, ""),
        (ARG, ["a b", "c"], "'a b' c"),
        (ARG, ("x", None), "x"),
        (UNFLAGGED, True, "--dry-run"),
        (UNFLAGGED, False, ""),
        (FLAGGED, True, "--sort"),
        (FLAGGED, "time", "--sort time"),
        (FLAGGED, ["a", "b c"], "--sort a --sort 'b c'"),
        (FLAGGED, None, ""),
    ],
)
def test_render_value(param: ParamSpec, value: object, expected: str) -> None:
    assert render_value(param, value) == expected


def test_render_value_raw_skips_quoting() -> None:
    assert render_value(ARG, "$HOME/*.txt", raw=True) == "$HOME/*.txt"


def test_render_command_substitutes_and_strips() -> None:
    spec = ShortcutSpec(
        name="s",
        command="ls {dry_run} {sort_by} {value} {value!r} {{x}} ",
        arguments=(ARG,),
        options=(FLAGGED, UNFLAGGED),
    )

    rendered = render_command(spec, {"value": "a b", "sort_by": None, "dry_run": True})

    assert rendered == "ls --dry-run  'a b' a b {x}"
