from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from config.settings import Settings

_LITELLM_ENV_NAMES = (
    "POLARIS_LITELLM_ENABLED",
    "POLARIS_LITELLM_BASE_URL",
    "POLARIS_LITELLM_API_KEY",
    "POLARIS_LITELLM_TIMEOUT_SECONDS",
    "POLARIS_LITELLM_MAX_CONCURRENCY",
    "POLARIS_LITELLM_REQUEST_BUDGET_TOKENS",
    "POLARIS_LITELLM_REJECT_MODEL_FALLBACK",
    "POLARIS_LITELLM_STRICT_MODE",
    "LITELLM_ENABLED",
    "LITELLM_BASE_URL",
    "LITELLM_API_KEY",
    "LITELLM_TIMEOUT_SECONDS",
    "LITELLM_MAX_CONCURRENCY",
    "LITELLM_REQUEST_BUDGET_TOKENS",
    "LITELLM_REJECT_MODEL_FALLBACK",
    "LITELLM_STRICT_MODE",
)


def _settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    overrides: dict[str, str] | None = None,
) -> Settings:
    monkeypatch.chdir(tmp_path)
    for name in _LITELLM_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    for name, value in (overrides or {}).items():
        monkeypatch.setenv(name, value)
    return Settings()


def test_litellm_settings_default_to_local_non_strict_gateway(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(monkeypatch, tmp_path)

    assert settings.LITELLM_ENABLED is False
    assert settings.LITELLM_BASE_URL == "http://localhost:4000/v1"
    assert settings.LITELLM_API_KEY is None
    assert settings.LITELLM_TIMEOUT_SECONDS == 60.0
    assert settings.LITELLM_MAX_CONCURRENCY == 1
    assert settings.LITELLM_REQUEST_BUDGET_TOKENS == 4096
    assert settings.LITELLM_REJECT_MODEL_FALLBACK is True
    assert settings.LITELLM_STRICT_MODE is False
    assert settings.DEFAULT_MODEL == "polaris-local-synthesis"

    settings.validate_litellm_gateway(require_configured=False)


def test_litellm_settings_read_polaris_prefixed_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(
        monkeypatch,
        tmp_path,
        overrides={
            "POLARIS_LITELLM_ENABLED": "true",
            "POLARIS_LITELLM_BASE_URL": " http://localhost:4000/v1/ ",
            "POLARIS_LITELLM_API_KEY": "local-test-key",
            "POLARIS_LITELLM_TIMEOUT_SECONDS": "45",
            "POLARIS_LITELLM_MAX_CONCURRENCY": "2",
            "POLARIS_LITELLM_REQUEST_BUDGET_TOKENS": "2048",
            "POLARIS_LITELLM_REJECT_MODEL_FALLBACK": "false",
            "POLARIS_LITELLM_STRICT_MODE": "true",
        },
    )

    assert settings.LITELLM_ENABLED is True
    assert settings.LITELLM_BASE_URL == "http://localhost:4000/v1"
    assert settings.LITELLM_API_KEY == "local-test-key"
    assert settings.LITELLM_TIMEOUT_SECONDS == 45.0
    assert settings.LITELLM_MAX_CONCURRENCY == 2
    assert settings.LITELLM_REQUEST_BUDGET_TOKENS == 2048
    assert settings.LITELLM_REJECT_MODEL_FALLBACK is False
    assert settings.LITELLM_STRICT_MODE is True

    settings.validate_litellm_gateway(require_configured=True)


def test_litellm_settings_validate_url_and_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError, match="POLARIS_LITELLM_BASE_URL"):
        _settings(
            monkeypatch,
            tmp_path,
            overrides={"POLARIS_LITELLM_BASE_URL": "localhost:4000/v1"},
        )

    with pytest.raises(ValidationError, match="LITELLM_TIMEOUT_SECONDS"):
        _settings(
            monkeypatch,
            tmp_path,
            overrides={"POLARIS_LITELLM_TIMEOUT_SECONDS": "0"},
        )

    with pytest.raises(ValidationError, match="LITELLM_MAX_CONCURRENCY"):
        _settings(
            monkeypatch,
            tmp_path,
            overrides={"POLARIS_LITELLM_MAX_CONCURRENCY": "0"},
        )

    with pytest.raises(ValidationError, match="LITELLM_REQUEST_BUDGET_TOKENS"):
        _settings(
            monkeypatch,
            tmp_path,
            overrides={"POLARIS_LITELLM_REQUEST_BUDGET_TOKENS": "0"},
        )


def test_litellm_strict_validation_reports_names_without_leaking_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(
        monkeypatch,
        tmp_path,
        overrides={
            "POLARIS_LITELLM_ENABLED": "false",
            "POLARIS_LITELLM_API_KEY": "sensitive-test-value",
        },
    )
    settings.LITELLM_API_KEY = None

    with pytest.raises(ValueError) as exc_info:
        settings.validate_litellm_gateway(require_configured=True)

    message = str(exc_info.value)
    assert "POLARIS_LITELLM_ENABLED" in message
    assert "POLARIS_LITELLM_API_KEY" in message
    assert "sensitive-test-value" not in message


def test_litellm_production_environment_requires_gateway_configuration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(monkeypatch, tmp_path)
    settings.ENVIRONMENT = "production"

    with pytest.raises(ValueError, match="LiteLLM gateway configuration"):
        settings.validate_litellm_gateway()
