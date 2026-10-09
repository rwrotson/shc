from typing import Final

from shc.config import Settings
from shc.services.plugins.registry import Registry, load_plugins
from shc.utils.shortcut_store import YamlShortcutStore

# Names of the root app's own command groups; shortcuts cannot use them.
RESERVED_NAMES: Final = frozenset({"config", "completion"})


def open_store(settings: Settings) -> YamlShortcutStore:
    """Return the store of the configured shortcuts file."""
    return YamlShortcutStore(settings.shortcuts.resolved_file)


def open_registry(settings: Settings) -> Registry:
    """Return the built-in plugins plus those in the configured plugin directory."""
    return load_plugins(settings.shortcuts.resolved_plugins_dir)
