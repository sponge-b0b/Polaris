from __future__ import annotations

from copy import deepcopy

from core.security.sensitive_data import (
    REDACTED_VALUE,
    sanitize_sensitive_mapping,
    sanitize_sensitive_value,
)


def test_sanitize_sensitive_mapping_redacts_nested_credentials_without_mutation() -> (
    None
):
    source = {
        "api_key": "top-secret",
        "nested": {
            "database_password": "db-secret",
            "safe": "visible",
        },
        "items": [{"authorization": "Bearer abc123"}],
    }
    original = deepcopy(source)

    sanitized = sanitize_sensitive_mapping(source)

    assert source == original
    assert sanitized == {
        "api_key": REDACTED_VALUE,
        "nested": {
            "database_password": REDACTED_VALUE,
            "safe": "visible",
        },
        "items": [{"authorization": REDACTED_VALUE}],
    }


def test_sanitize_sensitive_value_redacts_credentials_embedded_in_strings() -> None:
    database_url = "".join(
        (
            "postgresql+asyncpg://polaris:",
            "db-secret",
            "@localhost:5432/polaris",
        )
    )
    value = (
        "request failed authorization=Bearer-secret "
        "password=hunter2 "
        "header Bearer access-token "
        f"{database_url}"
    )

    sanitized = sanitize_sensitive_value(value)

    assert isinstance(sanitized, str)
    assert "Bearer-secret" not in sanitized
    assert "hunter2" not in sanitized
    assert "access-token" not in sanitized
    assert "db-secret" not in sanitized
    assert sanitized.count(REDACTED_VALUE) == 4
