from collections.abc import Callable
from pathlib import Path

import pytest

type WriteShortcuts = Callable[[str], Path]


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    return tmp_path / "user-config" / "shc"


@pytest.fixture
def write_shortcuts(config_dir: Path) -> WriteShortcuts:
    def write(text: str) -> Path:
        path = config_dir / "shortcuts.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    return write


@pytest.fixture
def write_plugin(config_dir: Path) -> Callable[[str, str], Path]:
    def write(name: str, source: str) -> Path:
        path = config_dir / "plugins" / f"{name}.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
        return path

    return write
