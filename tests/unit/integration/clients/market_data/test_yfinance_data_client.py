from __future__ import annotations

import asyncio
from typing import Any, cast

import httpx
import pandas as pd
import pytest

from core.telemetry.context import telemetry_context_scope
from core.telemetry.contracts.telemetry_context import TelemetryContext
from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from core.telemetry.events.telemetry_event import TelemetryEventLevel
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from integration.clients.market_data import yfinance_data_client as client_module
from domain.market.models import SP500Data
from integration.clients.market_data.yfinance_data_client import YFinanceClientOptions
from integration.clients.market_data.yfinance_data_client import YFinanceDataClient
from integration.providers.backtesting.market_data.simulated_data_provider import (
    SimulatedDataProvider,
)
from integration.providers.provider_telemetry import record_provider_call


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        text: str = "",
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.text = text
        self._payload = payload or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeAsyncClient:
    market_caps = {
        "AAA": 100.0,
        "BBB": 300.0,
        "BRK-B": 200.0,
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def __aenter__(self) -> FakeAsyncClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def get(
        self,
        url: str,
        **kwargs: Any,
    ) -> FakeResponse:
        if url == "https://fc.yahoo.com/":
            return FakeResponse()
        if url.endswith("/v1/test/getcrumb"):
            return FakeResponse(text="test-crumb")
        if "wikipedia.org" in url:
            return FakeResponse(text="constituent-table")
        if "/v8/finance/chart/" in url:
            symbol = url.rsplit("/", maxsplit=1)[-1]
            base = {
                "AAA": 10.0,
                "BBB": 20.0,
                "BRK-B": 30.0,
            }[symbol]
            return FakeResponse(
                payload={
                    "chart": {
                        "result": [
                            {
                                "timestamp": [
                                    1_700_000_000,
                                    1_700_086_400,
                                    1_700_172_800,
                                ],
                                "meta": {"exchangeTimezoneName": "UTC"},
                                "indicators": {
                                    "quote": [
                                        {
                                            "open": [base, base + 1.0, base + 2.0],
                                            "high": [
                                                base + 1.0,
                                                base + 2.0,
                                                base + 3.0,
                                            ],
                                            "low": [base - 1.0, base, base + 1.0],
                                            "close": [base, base + 1.0, base + 2.0],
                                            "volume": [100, 110, 120],
                                        }
                                    ]
                                },
                            }
                        ]
                    }
                }
            )
        if "/v10/finance/quoteSummary/" in url:
            symbol = url.rsplit("/", maxsplit=1)[-1]
            return FakeResponse(
                payload={
                    "quoteSummary": {
                        "result": [
                            {
                                "summaryDetail": {
                                    "marketCap": self.market_caps[symbol],
                                }
                            }
                        ]
                    }
                }
            )
        raise AssertionError(f"Unexpected URL: {url}")


@pytest.mark.asyncio
async def test_get_sp500_data_normalizes_canonical_breadth_schema_and_constituents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(client_module.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(
        client_module.pd,
        "read_html",
        lambda _: [pd.DataFrame({"Symbol": ["AAA", "BRK.B", "BBB"]})],
    )

    result = await YFinanceDataClient().get_sp500_data(
        interval="1d",
        days=3,
    )

    assert isinstance(result, SP500Data)
    assert result.top_50_constituents == ["BBB", "BRK-B", "AAA"]
    assert result.market_caps == {
        "AAA": 100.0,
        "BRK-B": 200.0,
        "BBB": 300.0,
    }
    assert list(result.analytics.columns) == [
        "market_cap_index",
        "advances_count",
        "declines_count",
        "unchanged_count",
        "active_count",
        "pct_above_50dma",
        "pct_above_200dma",
        "new_highs",
        "new_lows",
        "net_breadth",
        "breadth_percent",
        "ad_line",
        "ad_ratio",
    ]
    assert len(result.analytics) == 2
    assert result.analytics.index.is_monotonic_increasing
    assert {
        "new_high_low_diff",
        "new_high_low_ratio",
        "ad_line_ema_10",
        "ad_line_ema_20",
        "price_ad_divergence",
    }.isdisjoint(result.analytics.columns)


@pytest.mark.asyncio
async def test_simulated_sp500_data_matches_live_client_output_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(client_module.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(
        client_module.pd,
        "read_html",
        lambda _: [pd.DataFrame({"Symbol": ["AAA", "BRK.B", "BBB"]})],
    )

    live_result = await YFinanceDataClient().get_sp500_data(
        interval="1d",
        days=3,
    )
    simulated_result = await SimulatedDataProvider().get_sp500_data(days=3)

    assert type(simulated_result) is type(live_result) is SP500Data
    assert list(simulated_result.analytics.columns) == list(
        live_result.analytics.columns
    )
    assert all(
        isinstance(symbol, str) for symbol in simulated_result.top_50_constituents
    )
    assert all(
        isinstance(market_cap, float)
        for market_cap in simulated_result.market_caps.values()
    )


class SequencedAsyncClient:
    def __init__(self, outcomes: list[httpx.Response | BaseException]) -> None:
        self._outcomes = iter(outcomes)
        self.call_count = 0

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        del url, kwargs
        self.call_count += 1
        outcome = next(self._outcomes)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


async def _no_retry_sleep(_: float) -> None:
    return None


def _response(status_code: int) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        request=httpx.Request("GET", "https://query1.finance.yahoo.com/test"),
    )


def _build_integration_telemetry() -> tuple[
    IntegrationTelemetry,
    InMemoryTelemetrySink,
]:
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()
    observability_manager.add_sink(sink)
    return IntegrationTelemetry(observability_manager), sink


@pytest.mark.asyncio
async def test_request_emits_trace_correlated_retry_before_provider_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    telemetry, sink = _build_integration_telemetry()
    yahoo_client = YFinanceDataClient(
        options=YFinanceClientOptions(retry_attempts=2),
        telemetry=telemetry,
    )
    http_client = SequencedAsyncClient([_response(503), _response(200)])
    context = TelemetryContext(
        workflow_id="workflow-retry",
        execution_id="execution-retry",
        trace_id="trace-retry",
        span_id="span-retry",
        parent_span_id="parent-retry",
    )
    monkeypatch.setattr(client_module.asyncio, "sleep", _no_retry_sleep)

    with telemetry_context_scope(context):
        response = await record_provider_call(
            telemetry=telemetry,
            provider_name="LiveDataProvider",
            operation="get_symbol_data",
            call=lambda: yahoo_client._request(
                client=cast(httpx.AsyncClient, http_client),
                url="https://query1.finance.yahoo.com/test",
                operation="fetch_symbol_history",
            ),
        )

    assert response.status_code == 200
    assert http_client.call_count == 2
    assert [event.event_type for event in sink.events] == [
        "integration.client.retry_scheduled",
        "integration.provider.call",
    ]
    retry = sink.events[0]
    assert retry.level == TelemetryEventLevel.WARNING
    assert retry.success is None
    assert retry.trace_id == "trace-retry"
    assert retry.span_id is not None
    assert retry.span_id != "span-retry"
    assert retry.parent_span_id == "span-retry"
    assert retry.payload == {
        "provider_name": "YahooFinance",
        "client_name": "YFinanceDataClient",
        "operation": "fetch_symbol_history",
        "attempt": 1,
        "next_attempt": 2,
        "maximum_attempts": 2,
        "backoff_seconds": 0.25,
        "status_code": 503,
    }
    provider_events = [
        event
        for event in sink.events
        if event.event_type == "integration.provider.call"
    ]
    assert len(provider_events) == 1
    assert provider_events[0].success is True
    assert provider_events[0].trace_id == retry.trace_id
    assert provider_events[0].span_id == retry.span_id
    assert provider_events[0].parent_span_id == retry.parent_span_id


@pytest.mark.asyncio
async def test_request_emits_only_non_terminal_transport_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    telemetry, sink = _build_integration_telemetry()
    yahoo_client = YFinanceDataClient(
        options=YFinanceClientOptions(retry_attempts=2),
        telemetry=telemetry,
    )
    request = httpx.Request("GET", "https://query1.finance.yahoo.com/test")
    http_client = SequencedAsyncClient(
        [
            httpx.ConnectError("temporary outage", request=request),
            httpx.ConnectError("terminal outage", request=request),
        ]
    )
    monkeypatch.setattr(client_module.asyncio, "sleep", _no_retry_sleep)

    with pytest.raises(httpx.ConnectError, match="terminal outage"):
        await record_provider_call(
            telemetry=telemetry,
            provider_name="LiveDataProvider",
            operation="get_symbol_data",
            call=lambda: yahoo_client._request(
                client=cast(httpx.AsyncClient, http_client),
                url="https://query1.finance.yahoo.com/test",
                operation="fetch_symbol_history",
            ),
        )

    assert [event.event_type for event in sink.events] == [
        "integration.client.retry_scheduled",
        "integration.provider.call",
    ]
    assert sink.events[0].payload["error_type"] == "ConnectError"
    terminal = sink.events[1]
    assert terminal.success is False
    assert terminal.exception_details is not None
    assert terminal.exception_details.exception_type == "ConnectError"
    assert terminal.exception_details.message == "terminal outage"


@pytest.mark.asyncio
async def test_request_never_retries_cancellation() -> None:
    telemetry, sink = _build_integration_telemetry()
    yahoo_client = YFinanceDataClient(
        options=YFinanceClientOptions(retry_attempts=3),
        telemetry=telemetry,
    )
    http_client = SequencedAsyncClient([asyncio.CancelledError()])

    with pytest.raises(asyncio.CancelledError):
        await record_provider_call(
            telemetry=telemetry,
            provider_name="LiveDataProvider",
            operation="get_symbol_data",
            call=lambda: yahoo_client._request(
                client=cast(httpx.AsyncClient, http_client),
                url="https://query1.finance.yahoo.com/test",
                operation="fetch_symbol_history",
            ),
        )

    assert http_client.call_count == 1
    assert [event.event_type for event in sink.events] == [
        "integration.provider.cancelled"
    ]
