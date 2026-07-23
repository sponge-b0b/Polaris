from __future__ import annotations

import logging
from typing import cast

import pytest

from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from domain.macro.models import MacroDataSnapshot
from integration.clients.macro.fred_macro_client import (
    FredMacroClient,
    FredSeriesObservation,
)
from integration.providers.backtesting.macro.simulated_macro_provider import (
    SimulatedMacroProvider,
)
from integration.providers.macro.backtest_macro_provider import BacktestMacroProvider
from integration.providers.macro.live_macro_provider import LiveMacroProvider


class _FakeFredMacroClient:
    def __init__(
        self,
        *,
        values: dict[str, float | None] | None = None,
        failed_series: frozenset[str] = frozenset(),
    ) -> None:
        self.values = values or {}
        self.failed_series = failed_series
        self.requested_series: tuple[str, ...] = ()

    async def get_latest_observations(
        self,
        series_ids: tuple[str, ...],
    ) -> tuple[FredSeriesObservation, ...]:
        self.requested_series = series_ids
        return tuple(
            FredSeriesObservation(
                series_id=series_id,
                value=None
                if series_id in self.failed_series
                else self.values.get(series_id),
                error_type=(
                    "HTTPStatusError" if series_id in self.failed_series else None
                ),
                error_message=(
                    "FRED returned HTTP 503."
                    if series_id in self.failed_series
                    else None
                ),
            )
            for series_id in series_ids
        )


class _AllFailingFredMacroClient(_FakeFredMacroClient):
    async def get_latest_observations(
        self,
        series_ids: tuple[str, ...],
    ) -> tuple[FredSeriesObservation, ...]:
        self.requested_series = series_ids
        return tuple(
            FredSeriesObservation(
                series_id=series_id,
                value=None,
                error_type="ConnectError",
                error_message="FRED request failed with ConnectError.",
            )
            for series_id in series_ids
        )


def _build_telemetry() -> tuple[IntegrationTelemetry, InMemoryTelemetrySink]:
    sink = InMemoryTelemetrySink()
    manager = ObservabilityManager()
    manager.add_sink(sink)
    return IntegrationTelemetry(observability_manager=manager), sink


@pytest.mark.asyncio
async def test_live_macro_provider_normalizes_partial_batch_and_emits_telemetry(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake_client = _FakeFredMacroClient(
        values={
            "CPIAUCSL": 3.2,
            "CPILFESL": 3.4,
            "PCEPI": 2.8,
            "FEDFUNDS": 5.0,
            "DGS2": 4.4,
            "DGS10": 4.6,
            "UNRATE": 3.8,
            "M2SL": 20_000_000.0,
        },
        failed_series=frozenset({"VIXCLS"}),
    )
    telemetry, sink = _build_telemetry()
    provider = LiveMacroProvider(
        macro_client=cast(FredMacroClient, fake_client),
        telemetry=telemetry,
    )

    with caplog.at_level(logging.WARNING):
        snapshot = await provider.get_macro_snapshot()

    assert snapshot == MacroDataSnapshot(
        cpi=3.2,
        core_cpi=3.4,
        pce=2.8,
        fed_funds_rate=5.0,
        treasury_2y=4.4,
        treasury_10y=4.6,
        unemployment_rate=3.8,
        m2_money_supply=20_000_000.0,
        vix=None,
        failed_fields=("vix",),
    )
    assert fake_client.requested_series == (
        "CPIAUCSL",
        "CPILFESL",
        "PCEPI",
        "FEDFUNDS",
        "DGS2",
        "DGS10",
        "UNRATE",
        "M2SL",
        "VIXCLS",
    )
    assert "Macro provider series failed" in caplog.text
    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.success is True
    assert event.attributes["provider_name"] == "LiveMacroProvider"
    assert event.attributes["operation"] == "get_macro_snapshot"
    assert event.attributes["vendor"] == "fred"
    assert event.attributes["series_count"] == 9


@pytest.mark.asyncio
async def test_live_macro_provider_fails_when_every_series_fails() -> None:
    fake_client = _AllFailingFredMacroClient()
    telemetry, sink = _build_telemetry()
    provider = LiveMacroProvider(
        macro_client=cast(FredMacroClient, fake_client),
        telemetry=telemetry,
    )

    with pytest.raises(RuntimeError, match="All macro provider series failed"):
        await provider.get_macro_snapshot()

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.success is False
    assert event.payload["error_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_backtest_macro_provider_returns_deterministic_typed_snapshot() -> None:
    telemetry, sink = _build_telemetry()
    provider = BacktestMacroProvider(
        macro_provider=SimulatedMacroProvider(),
        telemetry=telemetry,
    )

    snapshot = await provider.get_macro_snapshot()

    assert snapshot == MacroDataSnapshot(
        cpi=0.0,
        core_cpi=0.0,
        pce=0.0,
        fed_funds_rate=0.0,
        treasury_2y=0.0,
        treasury_10y=0.0,
        unemployment_rate=0.0,
        m2_money_supply=0.0,
        vix=0.0,
    )
    assert snapshot.to_dict()["treasury_2y"] == 0.0
    assert len(sink.events) == 1
    assert sink.events[0].attributes["source"] == "simulated"
