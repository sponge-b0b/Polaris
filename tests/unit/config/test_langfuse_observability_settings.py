from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from pydantic import ValidationError

from config.settings import Settings
from tests.helpers.fake_langfuse import FakeLangfuseAiObservabilitySink

_LANGFUSE_ENV_NAMES = (
    "POLARIS_LANGFUSE_HOST",
    "POLARIS_LANGFUSE_PUBLIC_KEY",
    "POLARIS_LANGFUSE_SECRET_KEY",
    "POLARIS_LANGFUSE_ENVIRONMENT",
    "POLARIS_LANGFUSE_RELEASE",
    "POLARIS_LANGFUSE_SAMPLE_RATE",
    "POLARIS_LANGFUSE_CAPTURE_PROMPTS",
    "POLARIS_LANGFUSE_CAPTURE_RESPONSES",
    "POLARIS_LANGFUSE_CAPTURE_CONTEXTS",
    "POLARIS_LANGFUSE_CAPTURE_USER_INPUT",
    "POLARIS_LANGFUSE_REDACTION_MODE",
    "POLARIS_LANGFUSE_MAX_PAYLOAD_CHARACTERS",
    "POLARIS_LANGFUSE_MAX_METADATA_VALUE_CHARACTERS",
    "POLARIS_LANGFUSE_RETENTION_DAYS",
    "POLARIS_LANGFUSE_ALLOW_CLOUD_HOST",
    "LANGFUSE_HOST",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_ENVIRONMENT",
    "LANGFUSE_RELEASE",
    "LANGFUSE_SAMPLE_RATE",
    "LANGFUSE_CAPTURE_PROMPTS",
    "LANGFUSE_CAPTURE_RESPONSES",
    "LANGFUSE_CAPTURE_CONTEXTS",
    "LANGFUSE_CAPTURE_USER_INPUT",
    "LANGFUSE_REDACTION_MODE",
    "LANGFUSE_MAX_PAYLOAD_CHARACTERS",
    "LANGFUSE_MAX_METADATA_VALUE_CHARACTERS",
    "LANGFUSE_RETENTION_DAYS",
    "LANGFUSE_ALLOW_CLOUD_HOST",
)


def _settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    overrides: dict[str, str] | None = None,
) -> Settings:
    monkeypatch.chdir(tmp_path)
    for name in _LANGFUSE_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    for name, value in (overrides or {}).items():
        monkeypatch.setenv(name, value)
    return Settings()


def test_langfuse_settings_default_to_safe_local_capture_policy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(monkeypatch, tmp_path)

    assert settings.LANGFUSE_HOST is None
    assert settings.LANGFUSE_PUBLIC_KEY is None
    assert settings.LANGFUSE_SECRET_KEY is None
    assert settings.LANGFUSE_ENVIRONMENT == "development"
    assert settings.LANGFUSE_SAMPLE_RATE == 1.0
    assert settings.LANGFUSE_CAPTURE_PROMPTS is False
    assert settings.LANGFUSE_CAPTURE_RESPONSES is False
    assert settings.LANGFUSE_CAPTURE_CONTEXTS is False
    assert settings.LANGFUSE_CAPTURE_USER_INPUT is False
    assert settings.LANGFUSE_REDACTION_MODE == "strict"
    assert settings.LANGFUSE_MAX_PAYLOAD_CHARACTERS == 8_000
    assert settings.LANGFUSE_MAX_METADATA_VALUE_CHARACTERS == 512
    assert settings.LANGFUSE_RETENTION_DAYS == 90
    assert settings.LANGFUSE_ALLOW_CLOUD_HOST is False

    settings.validate_langfuse_observability(require_configured=False)


def test_langfuse_settings_read_polaris_prefixed_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(
        monkeypatch,
        tmp_path,
        overrides={
            "POLARIS_LANGFUSE_HOST": "https://langfuse.local",
            "POLARIS_LANGFUSE_PUBLIC_KEY": "public-key",
            "POLARIS_LANGFUSE_SECRET_KEY": "secret-key",
            "POLARIS_LANGFUSE_ENVIRONMENT": "staging",
            "POLARIS_LANGFUSE_RELEASE": "2026.07.12",
            "POLARIS_LANGFUSE_SAMPLE_RATE": "0.25",
            "POLARIS_LANGFUSE_CAPTURE_PROMPTS": "true",
            "POLARIS_LANGFUSE_REDACTION_MODE": "metadata_only",
            "POLARIS_LANGFUSE_MAX_PAYLOAD_CHARACTERS": "4096",
            "POLARIS_LANGFUSE_MAX_METADATA_VALUE_CHARACTERS": "256",
            "POLARIS_LANGFUSE_RETENTION_DAYS": "30",
        },
    )

    assert settings.LANGFUSE_HOST == "https://langfuse.local"
    assert settings.LANGFUSE_PUBLIC_KEY == "public-key"
    assert settings.LANGFUSE_SECRET_KEY == "secret-key"
    assert settings.LANGFUSE_ENVIRONMENT == "staging"
    assert settings.LANGFUSE_RELEASE == "2026.07.12"
    assert settings.LANGFUSE_SAMPLE_RATE == 0.25
    assert settings.LANGFUSE_CAPTURE_PROMPTS is True
    assert settings.LANGFUSE_REDACTION_MODE == "metadata_only"
    assert settings.LANGFUSE_MAX_PAYLOAD_CHARACTERS == 4096
    assert settings.LANGFUSE_MAX_METADATA_VALUE_CHARACTERS == 256
    assert settings.LANGFUSE_RETENTION_DAYS == 30

    settings.validate_langfuse_observability(require_configured=True)


def test_langfuse_validation_requires_production_credentials_without_leaking_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(
        monkeypatch,
        tmp_path,
        overrides={
            "POLARIS_LANGFUSE_HOST": "https://langfuse.local",
            "POLARIS_LANGFUSE_PUBLIC_KEY": "public-key",
            "POLARIS_LANGFUSE_SECRET_KEY": "super-secret-value",
        },
    )
    settings.LANGFUSE_SECRET_KEY = None

    with pytest.raises(ValueError) as exc_info:
        settings.validate_langfuse_observability(require_configured=True)

    message = str(exc_info.value)
    assert "POLARIS_LANGFUSE_SECRET_KEY" in message
    assert "super-secret-value" not in message
    assert "public-key" not in message


def test_langfuse_validation_requires_http_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(
        monkeypatch,
        tmp_path,
        overrides={"POLARIS_LANGFUSE_HOST": "langfuse.local"},
    )

    with pytest.raises(ValueError, match="POLARIS_LANGFUSE_HOST"):
        settings.validate_langfuse_observability(require_configured=False)


def test_langfuse_sample_rate_must_be_between_zero_and_one(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError, match="LANGFUSE_SAMPLE_RATE"):
        _settings(
            monkeypatch,
            tmp_path,
            overrides={"POLARIS_LANGFUSE_SAMPLE_RATE": "1.5"},
        )


def test_fake_langfuse_sink_records_payloads() -> None:
    sink = FakeLangfuseAiObservabilitySink()

    result = asyncio.run(sink.export({"observation": "rag.query"}))

    assert result.exported is True
    assert result.external_id == "fake-langfuse-1"
    assert sink.exported_payloads == [{"observation": "rag.query"}]


def test_langfuse_cloud_host_requires_explicit_governance_approval(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(
        monkeypatch,
        tmp_path,
        overrides={
            "POLARIS_LANGFUSE_HOST": "https://cloud.langfuse.com",
            "POLARIS_LANGFUSE_PUBLIC_KEY": "public-key",
            "POLARIS_LANGFUSE_SECRET_KEY": "secret-key",
        },
    )

    with pytest.raises(ValueError, match="Langfuse Cloud requires explicit approval"):
        settings.validate_langfuse_observability(require_configured=True)

    approved = _settings(
        monkeypatch,
        tmp_path,
        overrides={
            "POLARIS_LANGFUSE_HOST": "https://cloud.langfuse.com",
            "POLARIS_LANGFUSE_PUBLIC_KEY": "public-key",
            "POLARIS_LANGFUSE_SECRET_KEY": "secret-key",
            "POLARIS_LANGFUSE_ALLOW_CLOUD_HOST": "true",
        },
    )

    approved.validate_langfuse_observability(require_configured=True)


def test_langfuse_retention_and_payload_limits_must_be_positive(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError, match="LANGFUSE_RETENTION_DAYS"):
        _settings(
            monkeypatch, tmp_path, overrides={"POLARIS_LANGFUSE_RETENTION_DAYS": "0"}
        )
    with pytest.raises(ValidationError, match="LANGFUSE_MAX_PAYLOAD_CHARACTERS"):
        _settings(
            monkeypatch,
            tmp_path,
            overrides={"POLARIS_LANGFUSE_MAX_PAYLOAD_CHARACTERS": "0"},
        )
