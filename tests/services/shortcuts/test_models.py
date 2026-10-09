import pytest

from shc.services.shortcuts.models import ParamSpec, ShortcutSpec


def test_has_default_detects_value_and_factory() -> None:
    assert not ParamSpec(name="a", kind="argument").has_default
    assert ParamSpec(name="a", kind="argument", default=None).has_default
    assert ParamSpec(name="a", kind="argument", default_factory="cwd").has_default


def test_params_keeps_arguments_before_options() -> None:
    first = ParamSpec(name="first", kind="argument")
    second = ParamSpec(name="second", kind="option")
    spec = ShortcutSpec(name="s", command="x", arguments=(first,), options=(second,))

    assert spec.params == (first, second)
    assert spec.param("second") is second
    with pytest.raises(KeyError):
        spec.param("missing")
