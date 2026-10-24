"""Lossless, bounded JSON for Intelligence-owned facts and Evidence bases."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from importlib import import_module
from threading import RLock
from typing import Any
from uuid import UUID

from polaris.application.evidence.current_basis import CurrentEvidenceBasis

_ALLOWED_MODULE_PREFIXES = (
    "polaris.application.evidence.",
    "polaris.application.decisions.",
    "polaris.domain.",
)
_ALLOWED_OWNER_MODULES = frozenset(
    {
        "polaris.application.intelligence_judgment_history",
        "polaris.application.portfolio_context",
        "polaris.application.portfolio_judgment_history",
    }
)
_REGISTERED_TYPES: dict[str, type[Any]] = {}
_REGISTERED_TYPES_LOCK = RLock()


def register_owner_value_type(kind: type[Any]) -> None:
    """Admit an explicitly supplied owner proof type for durable basis capture."""
    if not isinstance(kind, type) or not (is_dataclass(kind) or issubclass(kind, Enum)):
        raise TypeError("owner value type must be a dataclass or enum")
    if "." in kind.__qualname__:
        raise TypeError("nested owner proof types are unsupported")
    name = f"{kind.__module__}:{kind.__name__}"
    with _REGISTERED_TYPES_LOCK:
        prior = _REGISTERED_TYPES.get(name)
        if prior is not None and prior is not kind:
            raise ValueError("owner proof type name is already registered")
        _REGISTERED_TYPES[name] = kind


def basis_payload(basis: CurrentEvidenceBasis) -> dict[str, object]:
    if type(basis) is not CurrentEvidenceBasis:
        raise TypeError("only a complete CurrentEvidenceBasis can be captured")
    value = contract_value_payload(basis)
    assert isinstance(value, dict)
    return value


def basis_from_payload(payload: object) -> CurrentEvidenceBasis:
    value = contract_value_from_payload(payload)
    if type(value) is not CurrentEvidenceBasis:
        raise ValueError("stored basis is not a complete CurrentEvidenceBasis")
    return value


def contract_value_payload(value: object) -> object:
    return _encode(value)


def contract_value_from_payload(payload: object) -> object:
    return _decode(payload)


def _type_name(value: object) -> str:
    kind = type(value)
    name = f"{kind.__module__}:{kind.__name__}"
    with _REGISTERED_TYPES_LOCK:
        registered = _REGISTERED_TYPES.get(name) is kind
    if (
        not kind.__module__.startswith(_ALLOWED_MODULE_PREFIXES)
        and kind.__module__ not in _ALLOWED_OWNER_MODULES
        and not registered
    ):
        raise TypeError(
            f"unsupported basis type: {kind.__module__}.{kind.__qualname__}"
        )
    if "." in kind.__qualname__:
        raise TypeError("nested basis classes are unsupported")
    return name


def _encode(value: object) -> object:
    if value is None or type(value) in (bool, int, float, str):
        return value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "$type": _type_name(value),
            "fields": {
                field.name: _encode(getattr(value, field.name))
                for field in fields(value)
            },
        }
    return _encode_special(value)


def _encode_special(value: object) -> object:
    if type(value) in (UUID, datetime, Decimal, timedelta):
        return _encode_scalar(value)
    if isinstance(value, Enum):
        return {"$enum": _type_name(value), "value": value.value}
    if type(value) is tuple:
        return {"$tuple": [_encode(item) for item in value]}
    if type(value) is frozenset:
        items = [_encode(item) for item in value]
        return {"$frozenset": sorted(items, key=_stable_key)}
    if type(value) is dict:
        pairs = [[_encode(key), _encode(item)] for key, item in value.items()]
        return {"$dict": sorted(pairs, key=lambda pair: _stable_key(pair[0]))}
    if type(value) is list:
        return {"$list": [_encode(item) for item in value]}
    raise TypeError(f"unsupported basis value: {type(value).__name__}")


def _encode_scalar(value: object) -> object:
    if type(value) is UUID:
        return {"$uuid": str(value)}
    if type(value) is datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("basis time must be timezone-aware")
        return {"$datetime": value.isoformat()}
    if type(value) is Decimal:
        return {"$decimal": str(value)}
    if type(value) is timedelta:
        return {
            "$timedelta_us": (
                value.days * 86_400_000_000
                + value.seconds * 1_000_000
                + value.microseconds
            )
        }
    raise TypeError("unsupported scalar basis value")


def _stable_key(value: object) -> str:
    import json

    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _allowed_type(name: object) -> type[Any]:
    if not isinstance(name, str) or name.count(":") != 1:
        raise ValueError("invalid stored basis type")
    module_name, class_name = name.split(":")
    if not class_name.isidentifier():
        raise ValueError("stored basis type is outside the allowed contract")
    with _REGISTERED_TYPES_LOCK:
        registered = _REGISTERED_TYPES.get(name)
    if registered is not None:
        return registered
    if (
        not module_name.startswith(_ALLOWED_MODULE_PREFIXES)
        and module_name not in _ALLOWED_OWNER_MODULES
    ):
        raise ValueError("stored basis type is outside the allowed contract")
    result = getattr(import_module(module_name), class_name, None)
    if not isinstance(result, type) or result.__module__ != module_name:
        raise ValueError("stored basis type is unavailable")
    return result


def _decode(value: object) -> object:
    if value is None or type(value) in (bool, int, float, str):
        return value
    if not isinstance(value, dict) or len(value) == 0:
        raise ValueError("invalid stored basis value")
    if "$type" in value:
        return _decode_dataclass(value)
    return _decode_tag(value)


def _decode_tag(value: dict[str, object]) -> object:
    if any(tag in value for tag in ("$uuid", "$datetime", "$decimal", "$timedelta_us")):
        return _decode_scalar(value)
    if "$enum" in value and set(value) == {"$enum", "value"}:
        kind = _allowed_type(value["$enum"])
        if not issubclass(kind, Enum):
            raise ValueError("stored basis enum type is invalid")
        return kind(value["value"])
    if "$tuple" in value and len(value) == 1 and isinstance(value["$tuple"], list):
        return tuple(_decode(item) for item in value["$tuple"])
    if (
        "$frozenset" in value
        and len(value) == 1
        and isinstance(value["$frozenset"], list)
    ):
        return frozenset(_decode(item) for item in value["$frozenset"])
    if "$dict" in value and len(value) == 1 and isinstance(value["$dict"], list):
        return {_decode(key): _decode(item) for key, item in value["$dict"]}
    if "$list" in value and len(value) == 1 and isinstance(value["$list"], list):
        return [_decode(item) for item in value["$list"]]
    raise ValueError("invalid stored basis tag")


def _decode_scalar(value: dict[str, object]) -> object:
    if "$uuid" in value and len(value) == 1:
        return UUID(str(value["$uuid"]))
    if "$datetime" in value and len(value) == 1:
        return datetime.fromisoformat(str(value["$datetime"]))
    if "$decimal" in value and len(value) == 1:
        return Decimal(str(value["$decimal"]))
    if "$timedelta_us" in value and len(value) == 1:
        micros = value["$timedelta_us"]
        if type(micros) is not int:
            raise ValueError("stored duration must be integer microseconds")
        return timedelta(microseconds=micros)
    raise ValueError("invalid stored basis tag")


def _decode_dataclass(value: dict[str, object]) -> object:
    if set(value) != {"$type", "fields"} or not isinstance(value["fields"], dict):
        raise ValueError("invalid stored dataclass tag")
    kind = _allowed_type(value["$type"])
    if not is_dataclass(kind):
        raise ValueError("stored basis class is not a dataclass")
    field_names = {field.name for field in fields(kind)}
    if set(value["fields"]) != field_names:
        raise ValueError("stored basis fields do not match their type")
    return kind(**{name: _decode(item) for name, item in value["fields"].items()})
