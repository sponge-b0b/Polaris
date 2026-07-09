from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.security.sensitive_data import REDACTED_VALUE
from core.security.sensitive_data import sanitize_sensitive_mapping
from core.security.sensitive_data import sanitize_sensitive_value


def sanitize_telemetry_value(
    value: Any,
    *,
    key: str | None = None,
) -> Any:
    """Return a copy safe for external logs and tracing exporters."""
    return sanitize_sensitive_value(
        value,
        key=key,
    )


def sanitize_telemetry_mapping(
    values: Mapping[str, Any],
) -> dict[str, Any]:
    """Sanitize a telemetry mapping without mutating the canonical event."""
    return sanitize_sensitive_mapping(values)


__all__ = [
    "REDACTED_VALUE",
    "sanitize_telemetry_mapping",
    "sanitize_telemetry_value",
]
