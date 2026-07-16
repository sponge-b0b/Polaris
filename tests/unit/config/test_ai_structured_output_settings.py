from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from config.settings import Settings

_STRUCTURED_AI_ENV_NAMES = (
    "POLARIS_STRUCTURED_OUTPUT_PROVIDER",
    "POLARIS_STRUCTURED_OUTPUT_MODEL",
    "POLARIS_STRUCTURED_OUTPUT_MAX_RETRIES",
    "POLARIS_STRUCTURED_OUTPUT_TIMEOUT_SECONDS",
    "POLARIS_STRUCTURED_OUTPUT_MAX_TOKENS",
    "POLARIS_STRUCTURED_OUTPUT_STRICT",
    "POLARIS_STRUCTURED_OUTPUT_INSTRUCTOR_MODE",
    "POLARIS_DSPY_ENABLED",
    "POLARIS_DSPY_OPTIMIZATION_MODEL",
    "POLARIS_DSPY_MAX_TRAINSET_CASES",
    "POLARIS_DSPY_ARTIFACT_RETENTION_DAYS",
    "STRUCTURED_OUTPUT_PROVIDER",
    "STRUCTURED_OUTPUT_MODEL",
    "STRUCTURED_OUTPUT_MAX_RETRIES",
    "STRUCTURED_OUTPUT_TIMEOUT_SECONDS",
    "STRUCTURED_OUTPUT_MAX_TOKENS",
    "STRUCTURED_OUTPUT_STRICT",
    "STRUCTURED_OUTPUT_INSTRUCTOR_MODE",
    "DSPY_ENABLED",
    "DSPY_OPTIMIZATION_MODEL",
    "DSPY_MAX_TRAINSET_CASES",
    "DSPY_ARTIFACT_RETENTION_DAYS",
)


def _settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    overrides: dict[str, str] | None = None,
) -> Settings:
    monkeypatch.chdir(tmp_path)
    for name in _STRUCTURED_AI_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    for name, value in (overrides or {}).items():
        monkeypatch.setenv(name, value)
    return Settings()


def test_structured_output_and_dspy_settings_default_to_safe_policy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(monkeypatch, tmp_path)

    assert settings.STRUCTURED_OUTPUT_PROVIDER == "instructor"
    assert settings.STRUCTURED_OUTPUT_MODEL == "polaris-local-structured"
    assert settings.STRUCTURED_OUTPUT_MAX_RETRIES == 2
    assert settings.STRUCTURED_OUTPUT_TIMEOUT_SECONDS == 60.0
    assert settings.STRUCTURED_OUTPUT_MAX_TOKENS == 4096
    assert settings.STRUCTURED_OUTPUT_STRICT is False
    assert settings.STRUCTURED_OUTPUT_INSTRUCTOR_MODE == "json"
    assert settings.DSPY_ENABLED is False
    assert settings.DSPY_OPTIMIZATION_MODEL == "polaris-local-optimization"
    assert settings.DSPY_MAX_TRAINSET_CASES == 100
    assert settings.DSPY_ARTIFACT_RETENTION_DAYS == 90


def test_structured_output_and_dspy_settings_read_polaris_prefixed_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(
        monkeypatch,
        tmp_path,
        overrides={
            "POLARIS_STRUCTURED_OUTPUT_PROVIDER": "INSTRUCTOR",
            "POLARIS_STRUCTURED_OUTPUT_MODEL": " qwen2.5:7b ",
            "POLARIS_STRUCTURED_OUTPUT_MAX_RETRIES": "3",
            "POLARIS_STRUCTURED_OUTPUT_TIMEOUT_SECONDS": "45",
            "POLARIS_STRUCTURED_OUTPUT_MAX_TOKENS": "2048",
            "POLARIS_STRUCTURED_OUTPUT_STRICT": "true",
            "POLARIS_STRUCTURED_OUTPUT_INSTRUCTOR_MODE": "TOOLS",
            "POLARIS_DSPY_ENABLED": "true",
            "POLARIS_DSPY_OPTIMIZATION_MODEL": " qwen3.5:4b ",
            "POLARIS_DSPY_MAX_TRAINSET_CASES": "25",
            "POLARIS_DSPY_ARTIFACT_RETENTION_DAYS": "30",
        },
    )

    assert settings.STRUCTURED_OUTPUT_PROVIDER == "instructor"
    assert settings.STRUCTURED_OUTPUT_MODEL == "qwen2.5:7b"
    assert settings.STRUCTURED_OUTPUT_MAX_RETRIES == 3
    assert settings.STRUCTURED_OUTPUT_TIMEOUT_SECONDS == 45.0
    assert settings.STRUCTURED_OUTPUT_MAX_TOKENS == 2048
    assert settings.STRUCTURED_OUTPUT_STRICT is True
    assert settings.STRUCTURED_OUTPUT_INSTRUCTOR_MODE == "tools"
    assert settings.DSPY_ENABLED is True
    assert settings.DSPY_OPTIMIZATION_MODEL == "qwen3.5:4b"
    assert settings.DSPY_MAX_TRAINSET_CASES == 25
    assert settings.DSPY_ARTIFACT_RETENTION_DAYS == 30


def test_structured_output_provider_is_validated(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError, match="STRUCTURED_OUTPUT_PROVIDER"):
        _settings(
            monkeypatch,
            tmp_path,
            overrides={"POLARIS_STRUCTURED_OUTPUT_PROVIDER": "unsupported"},
        )


def test_structured_output_instructor_mode_is_validated(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError, match="STRUCTURED_OUTPUT_INSTRUCTOR_MODE"):
        _settings(
            monkeypatch,
            tmp_path,
            overrides={"POLARIS_STRUCTURED_OUTPUT_INSTRUCTOR_MODE": "unsupported"},
        )


def test_structured_output_and_dspy_model_names_must_be_non_empty(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError, match="AI model names cannot be empty"):
        _settings(
            monkeypatch,
            tmp_path,
            overrides={"POLARIS_STRUCTURED_OUTPUT_MODEL": "   "},
        )
    with pytest.raises(ValidationError, match="AI model names cannot be empty"):
        _settings(
            monkeypatch,
            tmp_path,
            overrides={"POLARIS_DSPY_OPTIMIZATION_MODEL": "   "},
        )


def test_structured_output_and_dspy_numeric_limits_are_validated(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError, match="STRUCTURED_OUTPUT_MAX_RETRIES"):
        _settings(
            monkeypatch,
            tmp_path,
            overrides={"POLARIS_STRUCTURED_OUTPUT_MAX_RETRIES": "-1"},
        )
    with pytest.raises(ValidationError, match="STRUCTURED_OUTPUT_TIMEOUT_SECONDS"):
        _settings(
            monkeypatch,
            tmp_path,
            overrides={"POLARIS_STRUCTURED_OUTPUT_TIMEOUT_SECONDS": "0"},
        )
    with pytest.raises(ValidationError, match="STRUCTURED_OUTPUT_MAX_TOKENS"):
        _settings(
            monkeypatch,
            tmp_path,
            overrides={"POLARIS_STRUCTURED_OUTPUT_MAX_TOKENS": "0"},
        )
    with pytest.raises(ValidationError, match="DSPY_MAX_TRAINSET_CASES"):
        _settings(
            monkeypatch,
            tmp_path,
            overrides={"POLARIS_DSPY_MAX_TRAINSET_CASES": "0"},
        )
    with pytest.raises(ValidationError, match="DSPY_ARTIFACT_RETENTION_DAYS"):
        _settings(
            monkeypatch,
            tmp_path,
            overrides={"POLARIS_DSPY_ARTIFACT_RETENTION_DAYS": "0"},
        )
