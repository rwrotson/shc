import logging
from typing import Annotated

from typer import Context, Option, Typer

from shc.cli.callbacks import meta as meta_callbacks
from shc.cli.commands import completion_app, config_app
from shc.cli.context import AppContext
from shc.cli.shortcuts.group import ShortcutGroup
from shc.config import load_settings
from shc.utils.console import get_console
from shc.utils.output import OutputFormat

app = Typer(
    cls=ShortcutGroup,
    help="Run saved shortcuts for shell commands.",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config")
app.add_typer(completion_app, name="completion")


@app.callback()
def main(  # noqa: PLR0913, PLR0917  # Each parameter is a CLI option.
    ctx: Context,
    version: Annotated[  # noqa: ARG001
        bool,
        Option(
            "--version",
            "-v",
            help="Show the application's version and exit.",
            callback=meta_callbacks.version_cb,
            is_eager=True,
        ),
    ] = False,
    authors: Annotated[  # noqa: ARG001
        bool,
        Option(
            "--authors",
            "-A",
            help="Show the application's authors contacts and exit.",
            callback=meta_callbacks.authors_cb,
            is_eager=True,
        ),
    ] = False,
    verbose: Annotated[
        bool,
        Option(
            "--verbose",
            "-V",
            help="Enable verbose (DEBUG) logging.",
        ),
    ] = False,
    output_format: Annotated[
        OutputFormat,
        Option(
            "--output-format",
            "-f",
            help="Output format.",
        ),
    ] = OutputFormat.text,
    dry_run: Annotated[
        bool,
        Option(
            "--dry-run",
            "-n",
            help="Print the shortcut's command instead of running it.",
        ),
    ] = False,
) -> None:
    """Create the invocation context and set the logging level for CLI commands."""
    ctx.obj = AppContext(
        settings=load_settings(),
        console=get_console(),
        output_format=output_format,
        dry_run=dry_run,
    )
    if verbose:
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        for handler in root.handlers:
            handler.setLevel(logging.DEBUG)
