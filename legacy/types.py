from typing import Any, Callable

from click import Context, Parameter
from click.shell_completion import CompletionItem

type DefaultFactoryCallable = Callable[[], Any]
type ParserCallable = Callable[[str], Any]
type ShellCompleteCallable = Callable[[Context, Parameter, str], list[CompletionItem] | list[str]]
type AutocompletionCallable = Callable[..., Any]
