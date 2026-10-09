import sys
from pathlib import Path
from types import ModuleType

import pytest

from shc import plugin
from shc.services.errors import PluginError
from shc.services.plugins.markers import plugin_marks
from shc.services.plugins.registry import (
    PLUGIN_MODULE_PREFIX,
    Registry,
    builtin_registry,
    load_plugins,
)

PLUGIN_SOURCE = """
from dataclasses import dataclass

from shc import plugin
from shc.services.plugins.builtin_plugins import cwd


@dataclass
class Branch:
    name: str


@plugin.autocompletion("branches")
@plugin.parser("branch")
def branches(incomplete: str) -> list[str]:
    return [name for name in ("main", "dev") if name.startswith(incomplete)]
"""


def test_decorators_stack_marks_and_return_function() -> None:
    def func() -> None:
        pass

    decorated = plugin.parser("p")(plugin.default_factory("d")(plugin.autocompletion("a")(func)))

    assert decorated is func
    assert plugin_marks(func) == (
        ("autocompletion", "a"),
        ("default_factory", "d"),
        ("parser", "p"),
    )
    assert plugin_marks(object()) == ()


def test_registry_resolves_and_lists_names() -> None:
    registry = Registry()
    registry.register("parser", "b", str.upper)
    registry.register("parser", "a", str.lower)

    assert registry.resolve("parser", "a") is str.lower
    assert registry.names("parser") == ["a", "b"]
    assert registry.names("autocompletion") == []


def test_registry_rejects_duplicates_and_unknown_names() -> None:
    registry = Registry()
    registry.register("parser", "a", str.lower)

    with pytest.raises(PluginError, match="registered more than once"):
        registry.register("parser", "a", str.upper)
    with pytest.raises(PluginError, match="available: a"):
        registry.resolve("parser", "b")
    with pytest.raises(PluginError, match="available: none"):
        registry.resolve("autocompletion", "b")


def test_collect_skips_functions_imported_from_other_modules() -> None:
    @plugin.parser("foreign")
    def foreign(value: str) -> str:
        return value

    module = ModuleType("fake")
    vars(module)["foreign"] = foreign

    registry = Registry()
    registry.collect(module)

    assert registry.names("parser") == []


def test_builtin_registry_contents() -> None:
    registry = builtin_registry()

    assert registry.names("default_factory") == ["cwd", "home", "list", "now", "today", "tuple"]
    assert registry.names("autocompletion") == ["path"]
    assert registry.names("parser") == []


@pytest.mark.parametrize("directory", [None, Path("does-not-exist")])
def test_load_plugins_without_directory_returns_builtins(directory: Path | None) -> None:
    assert load_plugins(directory).names("autocompletion") == ["path"]


def test_load_plugins_imports_marked_functions(tmp_path: Path) -> None:
    (tmp_path / "git.py").write_text(PLUGIN_SOURCE)
    (tmp_path / "notes.txt").write_text("ignored")

    registry = load_plugins(tmp_path)

    complete = registry.resolve("autocompletion", "branches")
    assert complete("m") == ["main"]
    assert registry.resolve("parser", "branch") is complete
    assert registry.names("default_factory") == ["cwd", "home", "list", "now", "today", "tuple"]
    assert f"{PLUGIN_MODULE_PREFIX}.git" in sys.modules


def test_load_plugins_reports_broken_files(tmp_path: Path) -> None:
    (tmp_path / "broken.py").write_text("raise RuntimeError('boom')\n")

    with pytest.raises(PluginError, match=r"broken\.py: boom"):
        load_plugins(tmp_path)
    assert f"{PLUGIN_MODULE_PREFIX}.broken" not in sys.modules


def test_load_plugins_reports_duplicate_names_across_files(tmp_path: Path) -> None:
    source = (
        "from shc import plugin\n\n"
        "@plugin.autocompletion('path')\n"
        "def p(s: str) -> list[str]:\n"
        "    return []\n"
    )
    (tmp_path / "dup.py").write_text(source)

    with pytest.raises(PluginError, match="'path' is registered more than once"):
        load_plugins(tmp_path)


def test_plugin_error_uses_usage_exit_code() -> None:
    assert PluginError.exit_code == 2
