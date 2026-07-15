from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from config.settings import Settings

_DEEPEVAL_ENV_NAMES = (
    "POLARIS_DEEPEVAL_ENABLED",
    "POLARIS_DEEPEVAL_JUDGE_PROVIDER",
    "POLARIS_DEEPEVAL_JUDGE_MODEL",
    "POLARIS_DEEPEVAL_STRICT_MODE",
    "POLARIS_DEEPEVAL_TELEMETRY_OPT_OUT",
    "POLARIS_DEEPEVAL_DEFAULT_THRESHOLD",
    "POLARIS_DEEPEVAL_MAX_CONCURRENCY",
    "POLARIS_DEEPEVAL_TIMEOUT_SECONDS",
    "DEEPEVAL_ENABLED",
    "DEEPEVAL_JUDGE_PROVIDER",
    "DEEPEVAL_JUDGE_MODEL",
    "DEEPEVAL_STRICT_MODE",
    "DEEPEVAL_TELEMETRY_OPT_OUT",
    "DEEPEVAL_DEFAULT_THRESHOLD",
    "DEEPEVAL_MAX_CONCURRENCY",
    "DEEPEVAL_TIMEOUT_SECONDS",
)


def _settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    overrides: dict[str, str] | None = None,
) -> Settings:
    monkeypatch.chdir(tmp_path)
    for name in _DEEPEVAL_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    for name, value in (overrides or {}).items():
        monkeypatch.setenv(name, value)
    return Settings()


def test_deepeval_settings_default_to_enabled_safe_non_strict_policy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(monkeypatch, tmp_path)

    assert settings.DEEPEVAL_ENABLED is True
    assert settings.DEEPEVAL_JUDGE_PROVIDER is None
    assert settings.DEEPEVAL_JUDGE_MODEL is None
    assert settings.DEEPEVAL_STRICT_MODE is False
    assert settings.DEEPEVAL_TELEMETRY_OPT_OUT is True
    assert settings.DEEPEVAL_DEFAULT_THRESHOLD == 0.7
    assert settings.DEEPEVAL_MAX_CONCURRENCY == 4
    assert settings.DEEPEVAL_TIMEOUT_SECONDS == 60.0

    settings.validate_deepeval_evaluation(require_configured=False)


def test_deepeval_settings_read_polaris_prefixed_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(
        monkeypatch,
        tmp_path,
        overrides={
            "POLARIS_DEEPEVAL_ENABLED": "true",
            "POLARIS_DEEPEVAL_JUDGE_PROVIDER": "litellm",
            "POLARIS_DEEPEVAL_JUDGE_MODEL": "qwen3.5:4b",
            "POLARIS_DEEPEVAL_STRICT_MODE": "true",
            "POLARIS_DEEPEVAL_TELEMETRY_OPT_OUT": "true",
            "POLARIS_DEEPEVAL_DEFAULT_THRESHOLD": "0.82",
            "POLARIS_DEEPEVAL_MAX_CONCURRENCY": "2",
            "POLARIS_DEEPEVAL_TIMEOUT_SECONDS": "45",
        },
    )

    assert settings.DEEPEVAL_ENABLED is True
    assert settings.DEEPEVAL_JUDGE_PROVIDER == "litellm"
    assert settings.DEEPEVAL_JUDGE_MODEL == "qwen3.5:4b"
    assert settings.DEEPEVAL_STRICT_MODE is True
    assert settings.DEEPEVAL_TELEMETRY_OPT_OUT is True
    assert settings.DEEPEVAL_DEFAULT_THRESHOLD == 0.82
    assert settings.DEEPEVAL_MAX_CONCURRENCY == 2
    assert settings.DEEPEVAL_TIMEOUT_SECONDS == 45.0

    settings.validate_deepeval_evaluation(require_configured=True)


def test_deepeval_required_validation_reports_names_without_leaking_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(
        monkeypatch,
        tmp_path,
        overrides={
            "POLARIS_DEEPEVAL_JUDGE_PROVIDER": "provider-config-value",
            "POLARIS_DEEPEVAL_JUDGE_MODEL": "model-config-value",
        },
    )
    settings.DEEPEVAL_JUDGE_PROVIDER = None
    settings.DEEPEVAL_JUDGE_MODEL = None

    with pytest.raises(ValueError) as exc_info:
        settings.validate_deepeval_evaluation(require_configured=True)

    message = str(exc_info.value)
    assert "POLARIS_DEEPEVAL_JUDGE_PROVIDER" in message
    assert "POLARIS_DEEPEVAL_JUDGE_MODEL" in message
    assert "provider-config-value" not in message
    assert "model-config-value" not in message


def test_deepeval_strict_mode_requires_judge_configuration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(
        monkeypatch,
        tmp_path,
        overrides={"POLARIS_DEEPEVAL_STRICT_MODE": "true"},
    )

    with pytest.raises(ValueError, match="DeepEval LLM-evaluation configuration"):
        settings.validate_deepeval_evaluation()


def test_deepeval_disabled_fails_required_validation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(
        monkeypatch,
        tmp_path,
        overrides={
            "POLARIS_DEEPEVAL_ENABLED": "false",
            "POLARIS_DEEPEVAL_JUDGE_PROVIDER": "litellm",
            "POLARIS_DEEPEVAL_JUDGE_MODEL": "qwen3.5:4b",
        },
    )

    with pytest.raises(ValueError, match="POLARIS_DEEPEVAL_ENABLED"):
        settings.validate_deepeval_evaluation(require_configured=True)


def test_deepeval_numeric_limits_are_validated(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError, match="DEEPEVAL_DEFAULT_THRESHOLD"):
        _settings(
            monkeypatch,
            tmp_path,
            overrides={"POLARIS_DEEPEVAL_DEFAULT_THRESHOLD": "1.1"},
        )
    with pytest.raises(ValidationError, match="DEEPEVAL_MAX_CONCURRENCY"):
        _settings(
            monkeypatch,
            tmp_path,
            overrides={"POLARIS_DEEPEVAL_MAX_CONCURRENCY": "0"},
        )
    with pytest.raises(ValidationError, match="DEEPEVAL_TIMEOUT_SECONDS"):
        _settings(
            monkeypatch,
            tmp_path,
            overrides={"POLARIS_DEEPEVAL_TIMEOUT_SECONDS": "0"},
        )
