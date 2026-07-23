from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

REDACTED_VALUE = "[REDACTED]"

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "credentials",
        "password",
        "passwd",
        "private_key",
        "refresh_token",
        "secret",
        "secret_key",
        "set_cookie",
        "token",
        "access_token",
    }
)
_SENSITIVE_SUFFIXES = (
    "_api_key",
    "_authorization",
    "_credential",
    "_credentials",
    "_password",
    "_private_key",
    "_secret",
    "_token",
)
_SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|apikey|authorization|password|passwd|private[_-]?key|"
    r"refresh[_-]?token|secret(?:[_-]?key)?|access[_-]?token|token)"
    r"(\s*[:=]\s*)([^\s,;&]+)"
)
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[^\s,;&]+")
_URL_CREDENTIAL_PATTERN = re.compile(
    r"(?P<prefix>[a-z][a-z0-9+.-]*://[^:/@\s]+:)(?P<password>[^@\s]+)(?=@)",
    re.IGNORECASE,
)


def sanitize_sensitive_value(
    value: Any,
    *,
    key: str | None = None,
) -> Any:
    """Return a copy with credential-shaped keys and string fragments redacted."""
    if key is not None and _is_sensitive_key(key):
        return REDACTED_VALUE

    if isinstance(value, Mapping):
        return {
            str(nested_key): sanitize_sensitive_value(
                nested_value,
                key=str(nested_key),
            )
            for nested_key, nested_value in value.items()
        }

    if isinstance(value, tuple):
        return tuple(sanitize_sensitive_value(item) for item in value)

    if isinstance(value, list):
        return [sanitize_sensitive_value(item) for item in value]

    if isinstance(value, str):
        return _sanitize_sensitive_string(value)

    return value


def sanitize_sensitive_mapping(
    values: Mapping[str, Any],
) -> dict[str, Any]:
    """Sanitize a mapping without mutating the canonical source value."""
    return {
        str(key): sanitize_sensitive_value(
            value,
            key=str(key),
        )
        for key, value in values.items()
    }


def _is_sensitive_key(
    key: str,
) -> bool:
    normalized = key.strip().lower().replace("-", "_").replace(".", "_")
    return normalized in _SENSITIVE_KEYS or normalized.endswith(_SENSITIVE_SUFFIXES)


def _sanitize_sensitive_string(
    value: str,
) -> str:
    sanitized = _BEARER_PATTERN.sub(f"Bearer {REDACTED_VALUE}", value)
    sanitized = _URL_CREDENTIAL_PATTERN.sub(
        lambda match: f"{match.group('prefix')}{REDACTED_VALUE}",
        sanitized,
    )
    return _SENSITIVE_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}{REDACTED_VALUE}",
        sanitized,
    )
