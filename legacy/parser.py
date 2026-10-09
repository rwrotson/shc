import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Union

from typer import FileBinaryRead, FileText

_VALID_BASE_TYPES = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "tuple": tuple,
    "Path": Path,
    "datetime": datetime,
    "date": date,
    "FileText": FileText,
    "FileBinaryRead": FileBinaryRead,
    "None": type(None),
}

_VALID_GENERIC_TYPES = {
    "Optional": Optional,
    "Tuple": tuple,
    "|": Union,  # Union syntax support (`type1 | type2`)
}

def parse_typer_type(type_str: str):
    """Parses a type string and returns the corresponding Python type. Works for types supported by Typer"""

    if re.search(r"[\[\]{}().=<>!+*/&|^~-]", type_str) and not re.match(r"^[a-zA-Z0-9_|,\[\] ]+$", type_str):
        raise ValueError(f"Invalid type string: {type_str}. Potentially dangerous characters detected.")

    if type_str in _VALID_BASE_TYPES:
        return _VALID_BASE_TYPES[type_str]

    if type_str.startswith("Optional[") and type_str.endswith("]"):
        inner_type = parse_typer_type(type_str[9:-1])
        return Optional[inner_type]

    if type_str.startswith("Union[") and type_str.endswith("]"):
        inner_types = [parse_typer_type(t.strip()) for t in type_str[6:-1].split(",")]
        return Union[tuple(inner_types)]

    if type_str.lower().startswith("list[") and type_str.endswith("]"):
        inner_type = parse_typer_type(type_str[5:-1])
        return list[inner_type]

    if type_str.lower().startswith("tuple[") and type_str.endswith("]"):
        inner_types = [parse_typer_type(t.strip()) for t in type_str[6:-1].split(",")]
        return tuple[tuple(inner_types)]  # Convert to a tuple of types

    if " | " in type_str:
        union_types = [parse_typer_type(t.strip()) for t in type_str.split("|")]
        return Union[tuple(union_types)]

    raise ValueError(f"Invalid type string: {type_str}. Unsupported type format.")


def parse_path_type(type_str: str) -> type:
    """Parses a type string and returns the corresponding Python type. Works for types supported by Typer"""
    match type_str:
        case "str":
            return str
        case "bytes":
            return bytes
        case "None":
            return type(None)
        case _:
            raise ValueError(f"Invalid path type: {type_str}")


def parse_default_factory_callable(default_factory_str: str) -> callable:
    """Parses a default factory string and returns the corresponding callable"""
    match default_factory_str:
        case "list":
            return list
        case "tuple":
            return tuple
        case "datetime.now":
            return datetime.now
        case "date.today":
            return date.today
        case "Path.cwd":
            return Path.cwd
        case "Path.home":
            return Path.home
        case _:
            raise ValueError(f"Invalid default factory: {default_factory_str}")


def parse_parser_callable(parser_str: str) -> callable:
    """Parses a parser string and returns the corresponding callable"""
    match parser_str:
        case "parse_path_type":
            return parse_path_type
        case _:
            raise ValueError(f"Invalid parser: {parser_str}")


def parse_shell_complete_callable(shell_complete_str: str) -> callable:
    """Parses a shell complete string and returns the corresponding callable"""
    match shell_complete_str:
        case "complete_path":
            return complete_path
        case _:
            raise ValueError(f"Invalid shell complete: {shell_complete_str}")


def parse_autocompletion_callable(autocompletion_str: str) -> callable:
    """Parses an autocompletion string and returns the corresponding callable"""
    match autocompletion_str:
        case "complete_path":
            return complete_path
        case _:
            raise ValueError(f"Invalid autocompletion: {autocompletion_str}")
