import copy

import pytest

from shc.services.errors import (
    PluginError,
    ShortcutConfigError,
    ShortcutExistsError,
    ShortcutNotFoundError,
)
from shc.services.plugins.registry import builtin_registry
from shc.services.shortcuts.manage import (
    NewShortcut,
    add_shortcut,
    list_shortcuts,
    remove_shortcut,
    show_shortcut,
    to_plain,
    validate_shortcuts,
)
from shc.services.shortcuts.models import ParamSpec


class MemoryStore:
    def __init__(self, data: dict[str, object] | None = None) -> None:
        self.data: dict[str, object] = data or {}
        self.saves = 0

    @property
    def location(self) -> str:
        return "memory"

    def load(self) -> dict[str, object]:
        return copy.deepcopy(self.data)

    def save(self, data: dict[str, object]) -> None:
        self.data = copy.deepcopy(data)
        self.saves += 1


@pytest.fixture
def store() -> MemoryStore:
    return MemoryStore()


def test_add_infers_string_arguments(store: MemoryStore) -> None:
    new = NewShortcut(
        name="cp2",
        command="cp {src} {dst} {src!r}",
        description="Copy",
        requirements=("cp",),
    )

    spec = add_shortcut(store, new)

    assert spec.arguments == (
        ParamSpec(name="src", kind="argument"),
        ParamSpec(name="dst", kind="argument"),
    )
    assert store.data == {
        "shortcuts": {
            "cp2": {
                "command": "cp {src} {dst} {src!r}",
                "help": "Copy",
                "requirements": ["cp"],
                "arguments": [{"name": "src"}, {"name": "dst"}],
            }
        }
    }


def test_add_without_placeholders_keeps_entry_minimal(store: MemoryStore) -> None:
    add_shortcut(store, NewShortcut(name="up", command="cd .."))

    assert store.data == {"shortcuts": {"up": {"command": "cd .."}}}


def test_add_refuses_to_overwrite_without_force(store: MemoryStore) -> None:
    add_shortcut(store, NewShortcut(name="up", command="cd .."))

    with pytest.raises(ShortcutExistsError, match="--force"):
        add_shortcut(store, NewShortcut(name="up", command="cd ../.."))
    add_shortcut(store, NewShortcut(name="up", command="cd ../.."), force=True)

    assert store.data == {"shortcuts": {"up": {"command": "cd ../.."}}}


def test_add_validates_before_saving(store: MemoryStore) -> None:
    with pytest.raises(ShortcutConfigError, match="reserved"):
        add_shortcut(store, NewShortcut(name="config", command="x"), reserved={"config"})
    assert store.saves == 0


def test_add_rejects_malformed_document() -> None:
    store = MemoryStore({"shortcuts": ["a"]})

    with pytest.raises(ShortcutConfigError, match="must be a mapping"):
        add_shortcut(store, NewShortcut(name="up", command="cd .."))


def test_list_sorts_by_name() -> None:
    store = MemoryStore({"shortcuts": {"b": {"command": "b"}, "a": {"command": "a"}}})

    assert [spec.name for spec in list_shortcuts(store)] == ["a", "b"]


def test_show_returns_plain_entry() -> None:
    store = MemoryStore({"shortcuts": {"a": {"command": "a", "arguments": []}}})

    assert show_shortcut(store, "a") == {"command": "a", "arguments": []}
    with pytest.raises(ShortcutNotFoundError, match="'b'"):
        show_shortcut(store, "b")


def test_remove_deletes_entry() -> None:
    store = MemoryStore({"shortcuts": {"a": {"command": "a"}, "b": {"command": "b"}}})

    remove_shortcut(store, "a")

    assert store.data == {"shortcuts": {"b": {"command": "b"}}}
    with pytest.raises(ShortcutNotFoundError):
        remove_shortcut(store, "a")


def test_remove_from_empty_store_fails(store: MemoryStore) -> None:
    with pytest.raises(ShortcutNotFoundError):
        remove_shortcut(store, "a")


def test_validate_accepts_builtin_references() -> None:
    entry = {
        "command": "ls {path}",
        "arguments": [{"name": "path", "autocompletion": "path", "default_factory": "cwd"}],
    }
    store = MemoryStore({"shortcuts": {"l": entry}})

    parsed = validate_shortcuts(store, builtin_registry())

    assert list(parsed.shortcuts) == ["l"]


def test_validate_reports_all_unknown_plugins() -> None:
    entry = {
        "command": "ls {path} {sort}",
        "arguments": [{"name": "path", "autocompletion": "nope", "parser": "nada"}],
        "options": [{"name": "sort", "default_factory": "never"}],
    }
    store = MemoryStore({"shortcuts": {"l": entry}})

    with pytest.raises(PluginError) as excinfo:
        validate_shortcuts(store, builtin_registry())

    lines = str(excinfo.value).splitlines()
    assert len(lines) == 3
    assert lines[0].startswith("shortcut 'l' argument 'path': unknown autocompletion plugin 'nope'")


def test_to_plain_converts_nested_containers() -> None:
    class Ordered(dict[str, object]):
        pass

    assert to_plain(Ordered(a=[Ordered(b=1)])) == {"a": [{"b": 1}]}
