from __future__ import annotations

from typing import Any


def _clamp(value: float, lower: float = -1.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _get_value(
    source: Any,
    key: str,
    default: Any = None,
) -> Any:
    if source is None:
        return default

    if isinstance(source, dict):
        return source.get(key, default)

    return getattr(source, key, default)


def _last_or_none(
    values: list[Any],
) -> Any | None:
    if not values:
        return None

    return values[-1]


def _safe_bool(
    value: Any,
) -> bool:
    if value is None:
        return False

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {
            "true",
            "1",
            "yes",
            "y",
        }

    return bool(value)


def _safe_dict(
    value: Any,
) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(
    value: Any,
    default: int = 0,
) -> int:
    try:
        if value is None:
            return default

        return int(value)

    except Exception:
        return default


def _safe_list(
    value: Any,
) -> list[Any]:
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    return []


def _safe_str(
    value: Any,
    default: str = "",
) -> str:
    if value is None:
        return default

    try:
        return str(value)

    except Exception:
        return default
