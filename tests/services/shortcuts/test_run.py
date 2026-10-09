import pytest

from shc.services.errors import MissingRequirementError
from shc.services.shortcuts.models import ParamSpec, ShortcutSpec
from shc.services.shortcuts.run import RunResult, check_requirements, run_shortcut

ECHO = ShortcutSpec(
    name="say",
    command="echo {word}",
    arguments=(ParamSpec(name="word", kind="argument"),),
)


def test_dry_run_only_renders() -> None:
    spec = ShortcutSpec(name="x", command="exit 3", requirements=("no-such-binary-shc",))

    assert run_shortcut(spec, {}, dry_run=True) == RunResult(command="exit 3", returncode=None)


def test_run_executes_in_shell(capfd: pytest.CaptureFixture[str]) -> None:
    result = run_shortcut(ECHO, {"word": "hello world"})

    assert result == RunResult(command="echo 'hello world'", returncode=0)
    assert capfd.readouterr().out == "hello world\n"


def test_run_returns_child_exit_code() -> None:
    assert run_shortcut(ShortcutSpec(name="x", command="exit 3"), {}).returncode == 3


def test_run_checks_requirements_before_running() -> None:
    spec = ShortcutSpec(name="x", command="true", requirements=("sh", "no-such-binary-shc"))

    with pytest.raises(MissingRequirementError, match="no-such-binary-shc") as excinfo:
        run_shortcut(spec, {})
    assert "sh," not in str(excinfo.value)


def test_check_requirements_accepts_present_executables() -> None:
    check_requirements(["sh"])


def test_missing_requirement_uses_shell_exit_code() -> None:
    assert MissingRequirementError.exit_code == 127
