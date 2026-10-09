import stat
from pathlib import Path

import pytest

from shc.services.shortcuts.manage import NewShortcut, add_shortcut, remove_shortcut
from shc.utils.shortcut_store import YamlShortcutStore

DOCUMENT = """\
# My shortcuts
shortcuts:
  # Git
  gco:
    command: "git checkout {branch}"  # quoted on purpose
    arguments:
      - name: branch
"""


def test_location_is_the_path(tmp_path: Path) -> None:
    assert YamlShortcutStore(tmp_path / "s.yml").location == str(tmp_path / "s.yml")


def test_missing_and_empty_files_load_as_empty(tmp_path: Path) -> None:
    path = tmp_path / "s.yml"
    assert YamlShortcutStore(path).load() == {}

    path.write_text("# nothing yet\n")
    assert YamlShortcutStore(path).load() == {}


def test_load_returns_document(tmp_path: Path) -> None:
    path = tmp_path / "s.yml"
    path.write_text(DOCUMENT)

    assert YamlShortcutStore(path).load() == {
        "shortcuts": {
            "gco": {"command": "git checkout {branch}", "arguments": [{"name": "branch"}]}
        }
    }


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("shortcuts: [unclosed\n", "invalid YAML"),
        ("- a\n- b\n", "mapping at the top level"),
    ],
)
def test_load_rejects_malformed_documents(tmp_path: Path, content: str, message: str) -> None:
    path = tmp_path / "s.yml"
    path.write_text(content)

    with pytest.raises(ValueError, match=message):
        YamlShortcutStore(path).load()


def test_save_creates_directories_and_new_file(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dir" / "s.yml"

    YamlShortcutStore(path).save({"shortcuts": {"up": {"command": "cd .."}}})

    assert path.read_text() == "shortcuts:\n  up:\n    command: cd ..\n"
    assert stat.S_IMODE(path.stat().st_mode) == 0o644
    assert list(path.parent.iterdir()) == [path]


def test_save_keeps_existing_file_mode(tmp_path: Path) -> None:
    path = tmp_path / "s.yml"
    path.write_text(DOCUMENT)
    path.chmod(0o600)

    YamlShortcutStore(path).save({"shortcuts": {}})

    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_failed_save_leaves_original_and_no_temp_file(tmp_path: Path) -> None:
    path = tmp_path / "s.yml"
    path.write_text(DOCUMENT)

    with pytest.raises(Exception, match="cannot represent"):
        YamlShortcutStore(path).save({"shortcuts": object()})

    assert path.read_text() == DOCUMENT
    assert list(tmp_path.iterdir()) == [path]


def test_add_and_remove_keep_comments_and_quotes(tmp_path: Path) -> None:
    path = tmp_path / "s.yml"
    path.write_text(DOCUMENT)
    store = YamlShortcutStore(path)

    add_shortcut(store, NewShortcut(name="hi", command="echo hello {who}"))

    assert path.read_text() == DOCUMENT + (
        "  hi:\n    command: echo hello {who}\n    arguments:\n      - name: who\n"
    )

    remove_shortcut(store, "hi")

    assert path.read_text() == DOCUMENT
