from typing import Annotated

from rich.markup import escape
from typer import Argument, Context, Option, Typer

from shc.cli.context import get_app_context
from shc.services.example import run_example
from shc.utils.log import get_logger
from shc.utils.output import render_output
from shc.utils.stdin import read_stdin_if_piped

app = Typer()
log = get_logger()


@app.command()
def example_command(
    ctx: Context,
    argument: Annotated[
        str | None,
        Argument(
            help="Input value. Omit to read from stdin when piped.",
        ),
    ] = None,
    option: Annotated[
        int | None,
        Option(
            "-o",
            "--option",
            "--opt",
            help="Help text for integer option.",
        ),
    ] = None,
) -> None:
    """Display an argument and optional integer in text or JSON."""
    app_context = get_app_context(ctx)
    result = run_example(argument if argument is not None else read_stdin_if_piped(), option)

    log.debug("example_command invoked", argument=result.argument, option=result.option)

    render_output(
        {"argument": result.argument, "option": result.option},
        app_context.output_format,
        text_render=lambda: app_context.console.print(
            f"argument=[bold]{escape(result.argument)}[/bold] option={result.option}"
        ),
    )
