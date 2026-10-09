import pytest

from shc.services.errors import ShortcutConfigError
from shc.services.shortcuts.models import MISSING, ParamSpec, ShortcutSpec
from shc.services.shortcuts.parsing import parse_shortcut, parse_shortcuts


def shortcut(**overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "command": "git checkout {branch}",
        "arguments": [{"name": "branch"}],
    }
    entry.update(overrides)
    return entry


def test_parse_full_shortcut() -> None:
    data = {
        "shortcuts": {
            "gco": {
                "command": "git checkout {force} {branch} {mode}",
                "help": "Checkout a branch",
                "short_help": "Checkout",
                "epilog": "See git help checkout",
                "requirements": ["git"],
                "arguments": [
                    {"name": "branch", "type": "str", "autocompletion": "branches", "help": "B"}
                ],
                "options": [
                    {"name": "force", "type": "bool", "default": False, "flag": "-f"},
                    {
                        "name": "mode",
                        "choices": ["soft", "hard"],
                        "default": ["soft"],
                        "case_sensitive": False,
                        "min": 1,
                        "max": 2.5,
                        "show_default": "soft",
                        "formats": ["%Y"],
                        "path_type": "bytes",
                    },
                ],
            }
        }
    }

    parsed = parse_shortcuts(data)

    assert parsed.warnings == ()
    assert parsed.shortcuts == {
        "gco": ShortcutSpec(
            name="gco",
            command="git checkout {force} {branch} {mode}",
            help="Checkout a branch",
            short_help="Checkout",
            epilog="See git help checkout",
            requirements=("git",),
            arguments=(
                ParamSpec(name="branch", kind="argument", help="B", autocompletion="branches"),
            ),
            options=(
                ParamSpec(name="force", kind="option", type="bool", default=False, flag="-f"),
                ParamSpec(
                    name="mode",
                    kind="option",
                    choices=("soft", "hard"),
                    default=("soft",),
                    typer_options={
                        "case_sensitive": False,
                        "min": 1,
                        "max": 2.5,
                        "show_default": "soft",
                        "formats": ("%Y",),
                        "path_type": "bytes",
                    },
                ),
            ),
        )
    }


def test_param_defaults() -> None:
    param = parse_shortcut("gco", shortcut()).arguments[0]

    assert param.type == "str"
    assert param.default is MISSING
    assert param.typer_options == {}


@pytest.mark.parametrize("data", [{}, {"shortcuts": None}, {"shortcuts": {}}])
def test_empty_configuration(data: dict[str, object]) -> None:
    assert parse_shortcuts(data).shortcuts == {}


def test_unused_parameter_is_a_warning() -> None:
    data = {"shortcuts": {"hi": {"command": "echo hi", "options": [{"name": "loud"}]}}}

    assert parse_shortcuts(data).warnings == (
        "shortcut 'hi': option 'loud' is not used in the command",
    )


def test_reserved_name_is_rejected() -> None:
    with pytest.raises(ShortcutConfigError, match="'config' is reserved"):
        parse_shortcuts({"shortcuts": {"config": shortcut()}}, reserved={"config"})


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"commands": {}}, "configuration: unknown keys commands"),
        ({"shortcuts": []}, "must be a mapping of names"),
        ({"shortcuts": {"-bad": shortcut()}}, "invalid shortcut name"),
        ({"shortcuts": {"a": "echo"}}, "shortcut 'a' must be a mapping"),
        ({"shortcuts": {"a": shortcut(description="x")}}, "unknown keys description"),
        ({"shortcuts": {"a": {"command": "  "}}}, "non-empty 'command'"),
        ({"shortcuts": {"a": shortcut(help=1)}}, "'help' must be a string"),
        ({"shortcuts": {"a": shortcut(requirements="git")}}, "'requirements' must be a list"),
        ({"shortcuts": {"a": shortcut(arguments={})}}, "'arguments' must be a list"),
        ({"shortcuts": {"a": shortcut(arguments=["branch"])}}, "each argument must be a mapping"),
        ({"shortcuts": {"a": shortcut(arguments=[{"name": "my-arg"}])}}, "Python identifier"),
        ({"shortcuts": {"a": {"command": "echo {x}"}}}, "placeholder {x} has no matching"),
    ],
)
def test_invalid_shortcut(data: dict[str, object], message: str) -> None:
    with pytest.raises(ShortcutConfigError, match=message):
        parse_shortcuts(data)


@pytest.mark.parametrize(
    ("param", "message"),
    [
        ({"colour": "red"}, "unknown keys colour"),
        ({"type": 1}, "'type' must be a string"),
        ({"default": 1, "default_factory": "cwd"}, "are exclusive"),
        ({"choices": []}, "must not be empty"),
        ({"choices": [1]}, "'choices' must be a list of strings"),
        ({"min": True}, "'min' must be int or float"),
        ({"hidden": "yes"}, "'hidden' must be bool"),
        ({"formats": "%Y"}, "'formats' must be a list of strings"),
        ({"path_type": "int"}, "'path_type' must be one of"),
    ],
)
def test_invalid_argument(param: dict[str, object], message: str) -> None:
    entry = shortcut(arguments=[{"name": "branch", **param}])

    with pytest.raises(ShortcutConfigError, match=message):
        parse_shortcut("a", entry)


@pytest.mark.parametrize(
    ("option", "message"),
    [
        ({"flag": "force"}, "starting with '-'"),
        ({"flag": "-f -g"}, "single word"),
    ],
)
def test_invalid_option_flag(option: dict[str, object], message: str) -> None:
    entry = {"command": "x {force}", "options": [{"name": "force", **option}]}

    with pytest.raises(ShortcutConfigError, match=message):
        parse_shortcut("a", entry)


def test_flag_is_rejected_on_arguments() -> None:
    entry = shortcut(arguments=[{"name": "branch", "flag": "-b"}])

    with pytest.raises(ShortcutConfigError, match="only valid for options"):
        parse_shortcut("a", entry)


def test_duplicate_parameter_names_are_rejected() -> None:
    entry = shortcut(options=[{"name": "branch"}])

    with pytest.raises(ShortcutConfigError, match="declared twice"):
        parse_shortcut("a", entry)


def test_required_argument_cannot_follow_optional_one() -> None:
    entry = {
        "command": "x {a} {b}",
        "arguments": [{"name": "a", "default_factory": "cwd"}, {"name": "b"}],
    }

    with pytest.raises(ShortcutConfigError, match="'b' cannot follow optional argument 'a'"):
        parse_shortcut("s", entry)


def test_optional_arguments_may_follow_required_ones() -> None:
    entry = {"command": "x {a} {b}", "arguments": [{"name": "a"}, {"name": "b", "default": 1}]}

    assert [param.name for param in parse_shortcut("s", entry).arguments] == ["a", "b"]


@pytest.mark.parametrize("default", ["soft", ["soft", "hard"], None])
def test_choice_defaults_must_be_choices(default: object) -> None:
    option = {"name": "mode", "choices": ["soft", "hard"], "default": default}

    spec = parse_shortcut("s", {"command": "x {mode}", "options": [option]})

    assert spec.options[0].choices == ("soft", "hard")


@pytest.mark.parametrize("default", ["medium", ["soft", "medium"], {"a": 1}])
def test_choice_defaults_outside_choices_are_rejected(default: object) -> None:
    option = {"name": "mode", "choices": ["soft", "hard"], "default": default}

    with pytest.raises(ShortcutConfigError, match="'default' must be one of the choices"):
        parse_shortcut("s", {"command": "x {mode}", "options": [option]})
