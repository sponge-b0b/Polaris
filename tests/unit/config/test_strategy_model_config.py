from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from pydantic import ValidationError

from config.settings import Settings
from config.strategy_model_config import StrategyModelConfig

_STRATEGY_ENV_NAMES = (
    "POLARIS_STRATEGY_PERSPECTIVE_REASONING_MODEL",
    "STRATEGY_PERSPECTIVE_REASONING_MODEL",
    "POLARIS_STRATEGY_SYNTHESIS_MODEL",
    "STRATEGY_SYNTHESIS_MODEL",
)


def _settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    overrides: dict[str, str] | None = None,
) -> Settings:
    monkeypatch.chdir(tmp_path)
    for name in _STRATEGY_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    for name, value in (overrides or {}).items():
        monkeypatch.setenv(name, value)
    return Settings()


def test_strategy_model_config_defaults_to_approved_logical_aliases(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = StrategyModelConfig.from_settings(_settings(monkeypatch, tmp_path))

    assert config.perspective_reasoning_model == "polaris-local-reasoning"
    assert config.synthesis_model == "polaris-local-synthesis"


def test_strategy_model_config_preserves_independent_overrides(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = StrategyModelConfig.from_settings(
        _settings(
            monkeypatch,
            tmp_path,
            overrides={
                "POLARIS_STRATEGY_PERSPECTIVE_REASONING_MODEL": "reasoning-test",
                "POLARIS_STRATEGY_SYNTHESIS_MODEL": "synthesis-test",
            },
        )
    )

    assert config.perspective_reasoning_model == "reasoning-test"
    assert config.synthesis_model == "synthesis-test"


def test_strategy_model_config_is_immutable() -> None:
    config = StrategyModelConfig()

    with pytest.raises(FrozenInstanceError):
        setattr(config, "synthesis_" + "model", "replacement")


def test_strategy_model_config_rejects_empty_aliases(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError, match="AI model names cannot be empty"):
        _settings(
            monkeypatch,
            tmp_path,
            overrides={"POLARIS_STRATEGY_SYNTHESIS_MODEL": "   "},
        )
