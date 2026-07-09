from __future__ import annotations

import logging

import pytest

from core.bootstrap.di_providers import _select_provider


def test_invalid_provider_selection_uses_one_sanitized_emergency_record(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger_name = "core.telemetry.emitters.bootstrap_configuration_telemetry"
    selected_value = "secret-provider-value"

    with caplog.at_level(logging.CRITICAL, logger=logger_name):
        with pytest.raises(ValueError, match="MARKET_DATA_PROVIDER"):
            _select_provider(
                setting_name="MARKET_DATA_PROVIDER",
                selected=selected_value,
                candidates={},
            )

    records = [record for record in caplog.records if record.name == logger_name]
    assert len(records) == 1
    assert records[0].levelno == logging.CRITICAL
    assert selected_value not in caplog.text
