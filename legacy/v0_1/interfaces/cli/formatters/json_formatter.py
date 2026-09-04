from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import Any


def to_jsonable(
    value: Any,
) -> Any:
    to_dict = getattr(
        value,
        "to_dict",
        None,
    )

    if callable(to_dict):
        return to_jsonable(
            to_dict(),
        )

    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: to_jsonable(
                getattr(
                    value,
                    field.name,
                )
            )
            for field in fields(value)
        }

    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_jsonable(item) for item in value]

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, ModuleType):
        return {
            "type": "module",
            "name": value.__name__,
        }

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return repr(value)


def format_json(
    value: Any,
    *,
    indent: int = 2,
) -> str:
    return json.dumps(
        to_jsonable(value),
        indent=indent,
        sort_keys=True,
    )
