import shutil
import subprocess
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from shc.services.errors import MissingRequirementError
from shc.services.shortcuts.models import ShortcutSpec
from shc.services.shortcuts.render import render_command


@dataclass(frozen=True, slots=True)
class RunResult:
    """Rendered command and its exit code; no exit code for a dry run."""

    command: str
    returncode: int | None


def check_requirements(requirements: Iterable[str]) -> None:
    """Raise if any required executable is missing from PATH."""
    missing = [name for name in requirements if shutil.which(name) is None]
    if missing:
        raise MissingRequirementError(f"required executables not found: {', '.join(missing)}")


def run_shortcut(
    spec: ShortcutSpec, values: Mapping[str, object], *, dry_run: bool = False
) -> RunResult:
    """Render the shortcut's command and run it in the shell unless this is a dry run."""
    command = render_command(spec, values)
    if dry_run:
        return RunResult(command=command, returncode=None)
    check_requirements(spec.requirements)
    # Running the user's own shell command is the purpose of a shortcut.
    completed = subprocess.run(command, shell=True, check=False)  # noqa: S602
    return RunResult(command=command, returncode=completed.returncode)
