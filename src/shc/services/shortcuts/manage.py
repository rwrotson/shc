from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from typing import cast

from shc.services.errors import (
    PluginError,
    ShortcutConfigError,
    ShortcutExistsError,
    ShortcutNotFoundError,
)
from shc.services.plugins.markers import PluginKind
from shc.services.plugins.registry import Registry
from shc.services.shortcuts.models import ShortcutSpec
from shc.services.shortcuts.parsing import (
    SHORTCUTS_KEY,
    ParsedShortcuts,
    parse_shortcut,
    parse_shortcuts,
)
from shc.services.shortcuts.render import template_placeholders
from shc.services.shortcuts.store import ShortcutStore


def load_shortcuts(store: ShortcutStore, *, reserved: Collection[str] = ()) -> ParsedShortcuts:
    """Load and validate all shortcuts from the store."""
    return parse_shortcuts(store.load(), reserved=reserved)


def list_shortcuts(store: ShortcutStore, *, reserved: Collection[str] = ()) -> list[ShortcutSpec]:
    """Return all shortcuts sorted by name."""
    shortcuts = load_shortcuts(store, reserved=reserved).shortcuts
    return [shortcuts[name] for name in sorted(shortcuts)]


def show_shortcut(store: ShortcutStore, name: str) -> dict[str, object]:
    """Return the stored entry of one shortcut as plain data."""
    entries = _entries(store.load())
    if name not in entries:
        raise ShortcutNotFoundError(f"shortcut {name!r} is not defined")
    return cast(dict[str, object], to_plain(entries[name]))


@dataclass(frozen=True, slots=True)
class NewShortcut:
    """Input of `add_shortcut`; placeholders of the command become string arguments."""

    name: str
    command: str
    description: str | None = None
    requirements: tuple[str, ...] = ()

    def entry(self) -> dict[str, object]:
        """Build the configuration entry for the shortcut."""
        entry: dict[str, object] = {"command": self.command}
        if self.description is not None:
            entry["help"] = self.description
        if self.requirements:
            entry["requirements"] = list(self.requirements)
        placeholders = template_placeholders(self.command)
        if names := dict.fromkeys(placeholder.name for placeholder in placeholders):
            entry["arguments"] = [{"name": name} for name in names]
        return entry


def add_shortcut(
    store: ShortcutStore,
    new: NewShortcut,
    *,
    force: bool = False,
    reserved: Collection[str] = (),
) -> ShortcutSpec:
    """Add a shortcut to the store, replacing an existing one only with `force`."""
    data = store.load()
    entries = _entries(data)
    if new.name in entries and not force:
        raise ShortcutExistsError(
            f"shortcut {new.name!r} already exists; pass --force to replace it"
        )
    entry = new.entry()
    spec = parse_shortcut(new.name, entry, reserved=reserved)
    entries[new.name] = entry
    data[SHORTCUTS_KEY] = entries
    store.save(data)
    return spec


def remove_shortcut(store: ShortcutStore, name: str) -> None:
    """Delete a shortcut and save the store."""
    data = store.load()
    entries = _entries(data)
    if name not in entries:
        raise ShortcutNotFoundError(f"shortcut {name!r} is not defined")
    del entries[name]
    data[SHORTCUTS_KEY] = entries
    store.save(data)


def validate_shortcuts(
    store: ShortcutStore, registry: Registry, *, reserved: Collection[str] = ()
) -> ParsedShortcuts:
    """Validate the configuration and check that every referenced plugin is registered."""
    parsed = load_shortcuts(store, reserved=reserved)
    check_plugin_references(parsed.shortcuts.values(), registry)
    return parsed


def check_plugin_references(shortcuts: Iterable[ShortcutSpec], registry: Registry) -> None:
    """Raise one error listing every plugin name that the registry cannot resolve."""
    problems = []
    for spec in shortcuts:
        for param in spec.params:
            references: dict[PluginKind, str | None] = {
                "autocompletion": param.autocompletion,
                "default_factory": param.default_factory,
                "parser": param.parser,
            }
            for kind, plugin_name in references.items():
                if plugin_name is None:
                    continue
                try:
                    registry.resolve(kind, plugin_name)
                except PluginError as error:
                    problems.append(f"shortcut {spec.name!r} {param.kind} {param.name!r}: {error}")
    if problems:
        raise PluginError("\n".join(problems))


def to_plain(value: object) -> object:
    """Convert nested mappings and lists from a YAML loader into plain dicts and lists."""
    if isinstance(value, Mapping):
        return {str(key): to_plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_plain(item) for item in value]
    return value


def _entries(data: dict[str, object]) -> dict[str, object]:
    entries = data.get(SHORTCUTS_KEY)
    if entries is None:
        return {}
    if not isinstance(entries, dict):
        raise ShortcutConfigError(f"'{SHORTCUTS_KEY}' must be a mapping of names to shortcuts")
    return cast(dict[str, object], entries)
