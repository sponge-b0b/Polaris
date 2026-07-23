from __future__ import annotations

import json
from dataclasses import dataclass
from types import ModuleType

from interfaces.cli.formatters.json_formatter import format_json, to_jsonable


@dataclass(frozen=True, slots=True)
class ResultWithToDict:
    module: ModuleType

    def to_dict(self) -> dict[str, bool]:
        return {
            "safe": True,
        }


@dataclass(frozen=True, slots=True)
class DataclassWithModule:
    module: ModuleType


def test_to_jsonable_prefers_explicit_to_dict_over_dataclass_traversal() -> None:
    assert to_jsonable(
        ResultWithToDict(
            module=json,
        )
    ) == {
        "safe": True,
    }


def test_to_jsonable_handles_module_values_at_cli_boundary() -> None:
    assert to_jsonable(
        DataclassWithModule(
            module=json,
        )
    ) == {
        "module": {
            "type": "module",
            "name": "json",
        }
    }


def test_format_json_serializes_unpickleable_module_values() -> None:
    rendered = format_json(
        DataclassWithModule(
            module=json,
        )
    )

    assert json.loads(rendered) == {
        "module": {
            "type": "module",
            "name": "json",
        }
    }
