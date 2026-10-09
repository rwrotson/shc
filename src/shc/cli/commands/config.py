import os
import shlex
import subprocess
from collections.abc import Iterable
from typing import Annotated

import typer
from rich.markup import escape
from rich.table import Table

from shc.cli.context import AppContext, get_app_context
from shc.cli.shortcuts.builder import build_command
from shc.cli.shortcuts.loading import RESERVED_NAMES, open_registry, open_store
from shc.services.errors import ServiceError, ShortcutConfigError
from shc.services.plugins.registry import Registry
from shc.services.shortcuts.manage import (
    NewShortcut,
    add_shortcut,
    list_shortcuts,
    remove_shortcut,
    show_shortcut,
    validate_shortcuts,
)
from shc.services.shortcuts.models import ShortcutSpec
from shc.services.shortcuts.parsing import SHORTCUTS_KEY
from shc.services.shortcuts.store import write_document
from shc.utils.output import render_output
from shc.utils.shortcut_store import dump_yaml

app = typer.Typer(help="Manage the shortcuts configuration.")

ShortcutName = Annotated[str, typer.Argument(help="Shortcut name.", show_default=False)]


@app.command("list")
def list_command(ctx: typer.Context) -> None:
    """List configured shortcuts."""
    app_context = get_app_context(ctx)
    specs = list_shortcuts(open_store(app_context.settings), reserved=RESERVED_NAMES)
    rows = [
        {"name": spec.name, "help": spec.short_help or spec.help, "command": spec.command}
        for spec in specs
    ]

    def render_table() -> None:
        table = Table("Name", "Description", "Command")
        for row in rows:
            table.add_row(*(escape(row[key] or "") for key in ("name", "help", "command")))
        app_context.console.print(table)

    render_output(rows, app_context.output_format, text_render=render_table)


@app.command("show")
def show_command(ctx: typer.Context, name: ShortcutName) -> None:
    """Show the configuration of one shortcut."""
    app_context = get_app_context(ctx)
    entry = show_shortcut(open_store(app_context.settings), name)
    render_output(
        entry,
        app_context.output_format,
        text_render=lambda: typer.echo(dump_yaml({name: entry}), nl=False),
    )


@app.command("add")
def add_command(  # noqa: PLR0913, PLR0917  # Each parameter is a CLI option.
    ctx: typer.Context,
    name: ShortcutName,
    command: Annotated[
        str,
        typer.Argument(
            help="Command template; each {placeholder} becomes a string argument.",
            show_default=False,
        ),
    ],
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="Help text of the shortcut.")
    ] = None,
    requirements: Annotated[
        list[str] | None,
        typer.Option("--require", "-r", help="Executable that must be on PATH; repeatable."),
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", help="Replace an existing shortcut with the same name.")
    ] = False,
) -> None:
    """Add a shortcut to the configuration file."""
    app_context = get_app_context(ctx)
    new = NewShortcut(
        name=name,
        command=command,
        description=description,
        requirements=tuple(requirements or ()),
    )
    spec = add_shortcut(open_store(app_context.settings), new, force=force, reserved=RESERVED_NAMES)
    render_output(
        {"name": spec.name, "arguments": [param.name for param in spec.arguments]},
        app_context.output_format,
        text_render=lambda: app_context.console.print(
            f"Added shortcut [bold]{escape(spec.name)}[/bold]"
        ),
    )


@app.command("remove")
def remove_command(ctx: typer.Context, name: ShortcutName) -> None:
    """Remove a shortcut from the configuration file."""
    app_context = get_app_context(ctx)
    remove_shortcut(open_store(app_context.settings), name)
    render_output(
        {"name": name},
        app_context.output_format,
        text_render=lambda: app_context.console.print(
            f"Removed shortcut [bold]{escape(name)}[/bold]"
        ),
    )


@app.command("validate")
def validate_command(ctx: typer.Context) -> None:
    """Check the configuration and the plugins it references."""
    _validate(get_app_context(ctx))


@app.command("edit")
def edit_command(ctx: typer.Context) -> None:
    """Open the configuration file in $VISUAL or $EDITOR, then validate it."""
    app_context = get_app_context(ctx)
    store = open_store(app_context.settings)
    if not store.path.exists():
        write_document(store, {SHORTCUTS_KEY: {}})
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"
    # Runs the editor the user configured, as other CLI tools do.
    result = subprocess.run([*shlex.split(editor), str(store.path)], check=False)  # noqa: S603
    if result.returncode:
        raise typer.Exit(result.returncode)
    _validate(app_context)


@app.command("path")
def path_command(ctx: typer.Context) -> None:
    """Print the configuration file and plugin directory paths."""
    app_context = get_app_context(ctx)
    shortcuts = app_context.settings.shortcuts
    paths = {
        "file": str(shortcuts.resolved_file),
        "plugins_dir": str(shortcuts.resolved_plugins_dir),
    }
    render_output(
        paths,
        app_context.output_format,
        text_render=lambda: typer.echo(f"{paths['file']}\n{paths['plugins_dir']}"),
    )


def _validate(app_context: AppContext) -> None:
    settings = app_context.settings
    store = open_store(settings)
    registry = open_registry(settings)
    parsed = validate_shortcuts(store, registry, reserved=RESERVED_NAMES)
    _check_commands_build(parsed.shortcuts.values(), registry)

    def render_text() -> None:
        for warning in parsed.warnings:
            app_context.console.print(f"[warning]Warning:[/warning] {escape(warning)}")
        count = len(parsed.shortcuts)
        app_context.console.print(
            f"[info]{count} shortcut{'' if count == 1 else 's'} valid in "
            f"{escape(store.location)}[/info]"
        )

    render_output(
        {
            "file": store.location,
            "shortcuts": sorted(parsed.shortcuts),
            "warnings": list(parsed.warnings),
        },
        app_context.output_format,
        text_render=render_text,
    )


def _check_commands_build(specs: Iterable[ShortcutSpec], registry: Registry) -> None:
    problems = []
    for spec in specs:
        try:
            build_command(spec, registry)
        except ServiceError as error:
            problems.append(f"shortcut {spec.name!r}: {error}")
    if problems:
        raise ShortcutConfigError("\n".join(problems))
