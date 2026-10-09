from typing import Any

import typer
from typer.core import TyperGroup

from shc.cli.context import AppContext
from shc.services.errors import ServiceError
from shc.utils.output import OutputFormat, error_json


class ServiceErrorGroup(TyperGroup):
    """Report service errors on stderr and exit with their exit code."""

    # Typer passes its private vendored Click context, so the parameter is widened to Any.
    def invoke(self, ctx: Any) -> Any:  # noqa: ANN401
        """Run the command and convert service errors into exits."""
        try:
            return super().invoke(ctx)
        except ServiceError as error:
            if _output_format(ctx) == OutputFormat.json:
                error_json(type(error).__name__, str(error))
            else:
                typer.echo(f"Error: {error}", err=True)
            raise typer.Exit(error.exit_code) from error


def _output_format(ctx: Any) -> object:  # noqa: ANN401  # Typer's vendored Click context.
    app_context = ctx.find_object(AppContext)
    if app_context is not None:
        return app_context.output_format
    # Errors raised while resolving a subcommand happen before the root callback runs.
    params: dict[str, object] = ctx.find_root().params
    return params.get("output_format")
