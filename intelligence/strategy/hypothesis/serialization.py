from __future__ import annotations


def require_serialized_list(
    payload: dict[str, object],
    field_name: str,
) -> list[object]:
    """Return a required list from a serialized strategy payload."""

    if field_name not in payload:
        raise KeyError(f"missing required field: {field_name}")
    value = payload[field_name]
    if not isinstance(value, list):
        raise TypeError(f"{field_name} must be a list in serialized payloads.")
    return value
