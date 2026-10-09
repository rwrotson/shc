import inspect
import io
from enum import Enum, StrEnum
from types import GenericAlias
from typing import Annotated, Any, Final, cast

import typer
from typer.core import TyperCommand
from typer.main import get_command

from shc.cli.context import get_app_context
from shc.cli.shortcuts.types import Annotation, is_bool, parse_type
from shc.services.errors import ShortcutConfigError
from shc.services.plugins.registry import Registry
from shc.services.shortcuts.models import MISSING, ParamSpec, ShortcutSpec
from shc.services.shortcuts.render import render_command
from shc.services.shortcuts.run import run_shortcut
from shc.utils.log import get_logger
from shc.utils.output import render_output

# Name of the injected Typer context; shortcut parameters are Python identifiers without it.
CONTEXT_PARAM: Final = "_shc_context"
PATH_TYPES: Final[dict[str, type]] = {"str": str, "bytes": bytes}

log = get_logger()


def build_command(spec: ShortcutSpec, registry: Registry) -> TyperCommand:
    """Build a Typer command whose parameters follow the shortcut's declaration."""
    parameters = [
        inspect.Parameter(
            CONTEXT_PARAM, inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=typer.Context
        )
    ]
    parameters += [_build_parameter(param, registry) for param in spec.params]

    def callback(**values: object) -> None:
        ctx = cast(typer.Context, values.pop(CONTEXT_PARAM))
        _run(ctx, spec, {name: plain_value(value) for name, value in values.items()})

    # Typer reads parameters from the signature and their types from the annotations.
    vars(callback)["__signature__"] = inspect.Signature(parameters)
    callback.__annotations__ = {param.name: param.annotation for param in parameters}

    app = typer.Typer(add_completion=False)
    app.command(name=spec.name, help=spec.help, short_help=spec.short_help, epilog=spec.epilog)(
        callback
    )
    command = get_command(app)
    if not isinstance(command, TyperCommand):  # pragma: no cover - one command is never a group
        raise TypeError(f"expected a single command for shortcut {spec.name!r}")
    return command


def plain_value(value: object) -> object:
    """Convert Typer-parsed values into values the command template can render."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, io.IOBase):
        return getattr(value, "name", str(value))
    if isinstance(value, list | tuple):
        return [plain_value(item) for item in value]
    return value


def _run(ctx: typer.Context, spec: ShortcutSpec, values: dict[str, object]) -> None:
    app_context = get_app_context(ctx)
    log.debug("running shortcut", shortcut=spec.name, command=render_command(spec, values))
    result = run_shortcut(spec, values, dry_run=app_context.dry_run)
    if result.returncode is None:
        render_output(
            {"command": result.command},
            app_context.output_format,
            text_render=lambda: typer.echo(result.command),
        )
        return
    log.debug("shortcut finished", shortcut=spec.name, returncode=result.returncode)
    if result.returncode:
        raise typer.Exit(result.returncode)


def _build_parameter(param: ParamSpec, registry: Registry) -> inspect.Parameter:
    annotation = parse_type(param.type)
    choices = _choices_enum(param) if param.choices is not None else None
    if choices is not None:
        annotation = _with_choices(param, annotation, choices)

    info = _typer_info(param, registry)
    default: object = inspect.Parameter.empty
    if param.default is not MISSING:
        default = _enum_default(param, choices) if choices else param.default
    elif param.kind == "option" and param.default_factory is None:
        default = False if is_bool(annotation) else None
        if default is None:
            annotation = annotation | None

    typer_info = typer.Option(**info) if param.kind == "option" else typer.Argument(**info)
    return inspect.Parameter(
        param.name,
        inspect.Parameter.KEYWORD_ONLY,
        annotation=Annotated[annotation, typer_info],
        default=default,
    )


def _typer_info(param: ParamSpec, registry: Registry) -> dict[str, Any]:
    # Typer's keyword arguments are heterogeneous, so they are collected untyped.
    info: dict[str, Any] = {"help": param.help, **param.typer_options}
    if "path_type" in info:
        info["path_type"] = PATH_TYPES[info["path_type"]]
    if param.autocompletion is not None:
        info["autocompletion"] = registry.resolve("autocompletion", param.autocompletion)
    if param.parser is not None:
        info["parser"] = registry.resolve("parser", param.parser)
    if param.default_factory is not None:
        info["default_factory"] = registry.resolve("default_factory", param.default_factory)
        # The factory itself would be shown as a bound method; show its plugin name instead.
        info.setdefault("show_default", f"{param.default_factory}()")
    return info


def _choices_enum(param: ParamSpec) -> type[StrEnum]:
    members = [(choice, choice) for choice in param.choices or ()]
    # The functional Enum API returns a new class; typeshed types the call as an instance.
    return cast(type[StrEnum], StrEnum(f"{param.name}_choices", members))


def _with_choices(param: ParamSpec, annotation: Annotation, choices: type[StrEnum]) -> Annotation:
    replacements: dict[Annotation, Annotation] = {
        str: choices,
        str | None: choices | None,
        list[str]: GenericAlias(list, (choices,)),
        list[str] | None: GenericAlias(list, (choices,)) | None,
    }
    if annotation not in replacements:
        raise ShortcutConfigError(
            f"{param.kind} {param.name!r}: 'choices' requires type str or list[str]"
        )
    return replacements[annotation]


def _enum_default(param: ParamSpec, choices: type[StrEnum]) -> object:
    if isinstance(param.default, tuple):
        return [choices(str(value)) for value in param.default]
    return choices(str(param.default))
