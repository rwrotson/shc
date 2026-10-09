from typing import Protocol

from shc.services.errors import ShortcutConfigError, ShortcutStorageError


class ShortcutStore(Protocol):
    """Persistent storage of the shortcuts configuration document."""

    @property
    def location(self) -> str:
        """Human-readable location of the stored document."""
        ...

    def load(self) -> dict[str, object]:
        """Return the stored document, or an empty mapping if none exists.

        Raises `ValueError` for a malformed document and `OSError` if it cannot be read.
        """
        ...

    def save(self, data: dict[str, object]) -> None:
        """Replace the stored document; raises `OSError` if it cannot be written."""
        ...


def read_document(store: ShortcutStore) -> dict[str, object]:
    """Load the store's document, converting storage failures into service errors."""
    try:
        return store.load()
    except ValueError as error:
        raise ShortcutConfigError(str(error)) from error
    except OSError as error:
        raise ShortcutStorageError(f"cannot read {store.location}: {error}") from error


def write_document(store: ShortcutStore, data: dict[str, object]) -> None:
    """Save the document, converting storage failures into service errors."""
    try:
        store.save(data)
    except OSError as error:
        raise ShortcutStorageError(f"cannot write {store.location}: {error}") from error
