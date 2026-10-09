from typing import ClassVar


class ServiceError(Exception):
    """Base class for expected use-case failures reported by the CLI."""

    exit_code: ClassVar[int] = 1


class InvalidInputError(ServiceError):
    """The input cannot be processed."""

    # Matches Click's exit code for usage errors.
    exit_code = 2


class ShortcutConfigError(ServiceError):
    """The shortcuts configuration is malformed."""

    exit_code = 2


class ShortcutNotFoundError(ServiceError):
    """The requested shortcut is not defined."""


class ShortcutExistsError(ServiceError):
    """A shortcut with the same name is already defined."""


class MissingRequirementError(ServiceError):
    """An executable required by a shortcut is not on PATH."""

    # Matches the shell's exit code for a command that is not found.
    exit_code = 127


class PluginError(ServiceError):
    """A plugin cannot be loaded or a referenced plugin is not registered."""

    exit_code = 2


class ShortcutStorageError(ServiceError):
    """The shortcuts file cannot be read or written."""
