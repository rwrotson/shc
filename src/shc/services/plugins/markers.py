from collections.abc import Callable
from typing import Final, Literal, get_args

type PluginKind = Literal["autocompletion", "default_factory", "parser"]
type PluginFunction = Callable[..., object]
type PluginMark = tuple[PluginKind, str]

PLUGIN_KINDS: Final[tuple[PluginKind, ...]] = get_args(PluginKind.__value__)
_MARKS_ATTRIBUTE: Final = "__shc_plugins__"


def plugin_marks(value: object) -> tuple[PluginMark, ...]:
    """Return the registrations declared on a function by the decorators below."""
    marks: tuple[PluginMark, ...] = getattr(value, _MARKS_ATTRIBUTE, ())
    return marks


def _mark[F: PluginFunction](kind: PluginKind, name: str) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        setattr(func, _MARKS_ATTRIBUTE, (*plugin_marks(func), (kind, name)))
        return func

    return decorator


def autocompletion[F: PluginFunction](name: str) -> Callable[[F], F]:
    """Register a function as a completion source referenced by `autocompletion: <name>`."""
    return _mark("autocompletion", name)


def default_factory[F: PluginFunction](name: str) -> Callable[[F], F]:
    """Register a function as a default factory referenced by `default_factory: <name>`."""
    return _mark("default_factory", name)


def parser[F: PluginFunction](name: str) -> Callable[[F], F]:
    """Register a function as a value parser referenced by `parser: <name>`."""
    return _mark("parser", name)
