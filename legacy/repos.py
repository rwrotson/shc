from typing import Literal, TypedDict

from src.consts import PLUGINS_PATH
from src.types import DefaultFactoryCallable, ParserCallable, ShellCompleteCallable, AutocompletionCallable


REPO_NAMES = Literal[
    "default_factory",
    "parser",
    "shell_compete",
    "autocompletion",
]

class Repo(TypedDict):
    default_factory: dict[str, DefaultFactoryCallable]
    parser: dict[str, ParserCallable]
    shell_complete: dict[str, ShellCompleteCallable]
    autocompletion: dict[str, AutocompletionCallable]


def load_plugins() -> None:
    pass


def get_plugin(repo_name: str, plugin_name: str) ->