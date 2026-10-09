import pytest

from shc.services.errors import ShortcutConfigError, ShortcutStorageError
from shc.services.shortcuts.store import read_document, write_document


class FailingStore:
    def __init__(self, error: Exception) -> None:
        self.error = error

    @property
    def location(self) -> str:
        return "/s.yml"

    def load(self) -> dict[str, object]:
        raise self.error

    def save(self, data: dict[str, object]) -> None:
        raise self.error


def test_malformed_document_is_a_config_error() -> None:
    with pytest.raises(ShortcutConfigError, match="bad yaml"):
        read_document(FailingStore(ValueError("bad yaml")))


def test_unreadable_document_is_a_storage_error() -> None:
    with pytest.raises(ShortcutStorageError, match=r"cannot read /s\.yml: denied"):
        read_document(FailingStore(PermissionError("denied")))


def test_unwritable_document_is_a_storage_error() -> None:
    with pytest.raises(ShortcutStorageError, match=r"cannot write /s\.yml: full"):
        write_document(FailingStore(OSError("full")), {})


def test_storage_error_exit_code() -> None:
    assert ShortcutStorageError.exit_code == 1
