import importlib.util
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Final

from shc.services.errors import PluginError
from shc.services.plugins import builtin_plugins
from shc.services.plugins.markers import (
    PLUGIN_KINDS,
    PluginFunction,
    PluginKind,
    plugin_marks,
)

PLUGIN_MODULE_PREFIX: Final = "shc_plugins"


@dataclass(slots=True)
class Registry:
    """Named plugin functions grouped by kind."""

    entries: dict[PluginKind, dict[str, PluginFunction]] = field(
        default_factory=lambda: {kind: {} for kind in PLUGIN_KINDS}
    )

    def register(self, kind: PluginKind, name: str, func: PluginFunction) -> None:
        """Add a function; names must be unique within a kind."""
        if name in self.entries[kind]:
            raise PluginError(f"{kind} plugin {name!r} is registered more than once")
        self.entries[kind][name] = func

    def resolve(self, kind: PluginKind, name: str) -> PluginFunction:
        """Return the function registered under the name."""
        try:
            return self.entries[kind][name]
        except KeyError:
            available = ", ".join(self.names(kind)) or "none"
            raise PluginError(f"unknown {kind} plugin {name!r}; available: {available}") from None

    def names(self, kind: PluginKind) -> list[str]:
        """Return the registered names of a kind in sorted order."""
        return sorted(self.entries[kind])

    def collect(self, module: ModuleType) -> None:
        """Register the marked functions defined in the module."""
        for value in vars(module).values():
            if getattr(value, "__module__", None) != module.__name__:
                continue
            for kind, name in plugin_marks(value):
                self.register(kind, name, value)


def builtin_registry() -> Registry:
    """Return a registry with only the built-in plugins."""
    registry = Registry()
    registry.collect(builtin_plugins)
    return registry


def load_plugins(directory: Path | None) -> Registry:
    """Return the built-in plugins plus those defined in `*.py` files of the directory."""
    registry = builtin_registry()
    if directory is not None and directory.is_dir():
        for module in _import_modules(sorted(directory.glob("*.py"))):
            registry.collect(module)
    return registry


def _import_modules(paths: Iterable[Path]) -> Iterable[ModuleType]:
    for path in paths:
        module_name = f"{PLUGIN_MODULE_PREFIX}.{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise PluginError(f"cannot load plugin file {path}")
        module = importlib.util.module_from_spec(spec)
        # Dataclasses and pickling in plugin code look the module up by name.
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        # Plugin code is arbitrary; any failure is reported as a plugin error.
        except Exception as error:
            del sys.modules[module_name]
            raise PluginError(f"failed to load plugin {path}: {error}") from error
        yield module
