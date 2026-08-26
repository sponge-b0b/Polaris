from __future__ import annotations

from pathlib import Path

import pytest

from config.settings import Settings

_REPORT_ENV_NAMES = (
    "POLARIS_ENABLE_POSTGRES_REPORT_PERSISTENCE",
    "ENABLE_POSTGRES_REPORT_PERSISTENCE",
)


def _settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    overrides: dict[str, str] | None = None,
) -> Settings:
    monkeypatch.chdir(tmp_path)
    for name in _REPORT_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    for name, value in (overrides or {}).items():
        monkeypatch.setenv(name, value)
    return Settings()


def test_report_persistence_defaults_to_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(monkeypatch, tmp_path)

    assert settings.ENABLE_POSTGRES_REPORT_PERSISTENCE is False


@pytest.mark.parametrize("value", ["1", "true", "yes", "on"])
def test_report_persistence_reads_polaris_prefixed_boolean_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    value: str,
) -> None:
    settings = _settings(
        monkeypatch,
        tmp_path,
        overrides={"POLARIS_ENABLE_POSTGRES_REPORT_PERSISTENCE": value},
    )

    assert settings.ENABLE_POSTGRES_REPORT_PERSISTENCE is True
