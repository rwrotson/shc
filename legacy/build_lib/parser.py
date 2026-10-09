import re
from datetime import datetime, date
from typing import Optional, Union
from pathlib import Path

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

