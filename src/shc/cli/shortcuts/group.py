from typing import Any, Final

from typer.core import TyperCommand

from shc.cli.errors import ServiceErrorGroup
from shc.cli.shortcuts.builder import build_command
from shc.cli.shortcuts.loading import RESERVED_NAMES, open_registry, open_store
from shc.config import load_settings
from shc.services.errors import ServiceError
from shc.services.shortcuts.manage import load_shortcuts
from shc.utils.log import get_logger

# Key in `ctx.meta`, which every context of one invocation shares.
_SHORTCUTS_META_KEY: Final = "shc.shortcuts"

type _Shortcuts = dict[str, TyperCommand | ServiceError]

log = get_logger()


class ShortcutGroup(ServiceErrorGroup):
    """Root group that adds a command for every configured shortcut."""

    # Typer passes its private vendored Click context, so the parameter is widened to Any.
    def list_commands(self, ctx: Any) -> list[str]:  # noqa: ANN401
        """List built-in commands, then the shortcuts that build without errors."""
        static = super().list_commands(ctx)
        try:
            shortcuts = _shortcuts(ctx)
        except ServiceError as error:
            log.warning("shortcuts are unavailable", error=str(error))
            return static
        for name, command in shortcuts.items():
            if isinstance(command, ServiceError):
                log.warning("shortcut skipped", shortcut=name, error=str(command))
        return static + sorted(
            name for name, command in shortcuts.items() if isinstance(command, TyperCommand)
        )

    def get_command(self, ctx: Any, cmd_name: str) -> Any:  # noqa: ANN401
        """Return a built-in command or the shortcut's command; raise its build error."""
        command = super().get_command(ctx, cmd_name)
        if command is not None:
            return command
        shortcut = _shortcuts(ctx).get(cmd_name)
        if isinstance(shortcut, ServiceError):
            raise shortcut
        return shortcut


def _shortcuts(ctx: Any) -> _Shortcuts:  # noqa: ANN401  # Typer's vendored Click context.
    meta: dict[str, Any] = ctx.meta
    if _SHORTCUTS_META_KEY not in meta:
        meta[_SHORTCUTS_META_KEY] = _build_shortcuts()
    shortcuts: _Shortcuts = meta[_SHORTCUTS_META_KEY]
    return shortcuts


def _build_shortcuts() -> _Shortcuts:
    settings = load_settings()
    specs = load_shortcuts(open_store(settings), reserved=RESERVED_NAMES).shortcuts
    if not specs:
        return {}
    registry = open_registry(settings)
    shortcuts: _Shortcuts = {}
    for name, spec in specs.items():
        try:
            shortcuts[name] = build_command(spec, registry)
        except ServiceError as error:
            shortcuts[name] = error
    return shortcuts
