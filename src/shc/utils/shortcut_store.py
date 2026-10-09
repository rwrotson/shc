import io
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_NEW_FILE_MODE = 0o644


class YamlShortcutStore:
    """Shortcuts document in a YAML file; round-trip loading keeps comments and key order."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @property
    def location(self) -> str:
        """Path of the YAML file."""
        return str(self.path)

    def load(self) -> dict[str, object]:
        """Return the document, or an empty mapping if the file is missing or empty."""
        if not self.path.exists():
            return {}
        try:
            with self.path.open(encoding="utf-8") as stream:
                data: object = _yaml().load(stream)
        except YAMLError as error:
            raise ValueError(f"invalid YAML in {self.path}: {error}") from error
        if data is None:
            return {}
        if not isinstance(data, Mapping):
            raise ValueError(f"{self.path} must contain a mapping at the top level")
        # The round-trip loader returns CommentedMap, a dict subclass that keeps comments.
        return cast(dict[str, object], data)

    def save(self, data: dict[str, object]) -> None:
        """Write the document atomically, creating parent directories as needed."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            dir=self.path.parent, prefix=f".{self.path.name}.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                _yaml().dump(data, stream)
            # mkstemp creates the file with mode 0600; keep the mode of the replaced file.
            mode = self.path.stat().st_mode if self.path.exists() else _NEW_FILE_MODE
            Path(temp_name).chmod(mode & 0o777)
            Path(temp_name).replace(self.path)
        except BaseException:
            Path(temp_name).unlink(missing_ok=True)
            raise


def dump_yaml(data: object) -> str:
    """Serialize data as block-style YAML."""
    stream = io.StringIO()
    _yaml().dump(data, stream)
    return stream.getvalue()


def _yaml() -> YAML:
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    return yaml
