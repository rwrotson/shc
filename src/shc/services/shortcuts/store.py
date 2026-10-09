from typing import Protocol


class ShortcutStore(Protocol):
    """Persistent storage of the shortcuts configuration document."""

    @property
    def location(self) -> str:
        """Human-readable location of the stored document."""
        ...

    def load(self) -> dict[str, object]:
        """Return the stored document, or an empty mapping if none exists."""
        ...

    def save(self, data: dict[str, object]) -> None:
        """Replace the stored document."""
        ...
