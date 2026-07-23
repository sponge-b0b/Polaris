from __future__ import annotations

from core.security.sensitive_data import REDACTED_VALUE
from core.telemetry.sanitization import (
    sanitize_telemetry_mapping,
    sanitize_telemetry_value,
)


def test_telemetry_sanitization_uses_canonical_sensitive_data_policy() -> None:
    assert sanitize_telemetry_mapping(
        {
            "api_key": "secret",
            "detail": "request failed password=hunter2",
        }
    ) == {
        "api_key": REDACTED_VALUE,
        "detail": f"request failed password={REDACTED_VALUE}",
    }
    sanitized_header = sanitize_telemetry_value("Authorization: Bearer token-value")

    assert "token-value" not in sanitized_header
    assert REDACTED_VALUE in sanitized_header
