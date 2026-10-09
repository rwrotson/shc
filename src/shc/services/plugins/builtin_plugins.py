from datetime import UTC, date, datetime
from pathlib import Path

from shc.services.plugins.markers import autocompletion, default_factory


@default_factory("list")
def empty_list() -> list[object]:
    """Return a new empty list."""
    return []


@default_factory("tuple")
def empty_tuple() -> tuple[object, ...]:
    """Return an empty tuple."""
    return ()


@default_factory("now")
def now() -> datetime:
    """Return the current local time with its time zone."""
    return datetime.now(UTC).astimezone()


@default_factory("today")
def today() -> date:
    """Return the current local date."""
    return now().date()


@default_factory("cwd")
def cwd() -> Path:
    """Return the current working directory."""
    return Path.cwd()


@default_factory("home")
def home() -> Path:
    """Return the user's home directory."""
    return Path.home()


@autocompletion("path")
def complete_path(incomplete: str) -> list[str]:
    """Complete file system paths; directories end with a slash."""
    typed = Path(incomplete).expanduser()
    if incomplete.endswith("/"):
        parent, prefix = typed, ""
    else:
        parent, prefix = typed.parent, typed.name
    if not parent.is_dir():
        return []
    base = incomplete[: len(incomplete) - len(prefix)]
    return sorted(
        base + child.name + ("/" if child.is_dir() else "")
        for child in parent.iterdir()
        if child.name.startswith(prefix)
    )
