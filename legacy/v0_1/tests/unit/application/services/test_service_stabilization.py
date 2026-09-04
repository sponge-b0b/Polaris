from __future__ import annotations

from typing import Any, cast

import pytest

from application.services.base import ServiceRequest, ServiceResult, ServiceRunner
from application.services.macro.macro_request import MacroAnalysisRequest
from application.services.macro.macro_service import MacroService
from application.services.market_events.market_events_request import MarketEventsRequest
from application.services.market_events.market_events_service import MarketEventsService
from application.services.news.news_request import NewsRequest
from application.services.news.news_service import NewsService
from application.services.portfolio.portfolio_request import PortfolioAnalysisRequest
from application.services.portfolio.portfolio_service import PortfolioService
from application.services.sentiment import sentiment_analysis, sentiment_fusion
from application.services.sentiment.sentiment_request import SentimentSnapshotRequest
from application.services.sentiment.sentiment_result import SentimentSnapshotResult
from application.services.sentiment.sentiment_service import SentimentService
from application.services.technical.technical_analysis_service import (
    TechnicalAnalysisService,
)
from application.services.technical.technical_request import TechnicalAnalysisRequest
from core.llm.llm_service import LLMService
from core.runtime.state.runtime_context import RuntimeContext
from core.telemetry.emitters.application_service_telemetry import (
    ApplicationServiceTelemetry,
)
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from domain.macro.models import MacroDataSnapshot
from integration.providers.macro.macro_provider import MacroProvider
from integration.providers.market_events.market_events_provider import (
    MarketEventsProvider,
)
from integration.providers.news.news_provider import NewsProvider
from integration.providers.sentiment.sentiment_provider import SentimentProvider
from intelligence.research.sentiment.sentiment_agent import SentimentAgent


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("service", "request_name"),
    [
        (
            TechnicalAnalysisService(data_provider=cast(Any, object())),
            "TechnicalAnalysisRequest",
        ),
        (
            MarketEventsService(events_provider=cast(MarketEventsProvider, object())),
            "MarketEventsRequest",
        ),
        (
            NewsService(news_provider=cast(NewsProvider, object())),
            "NewsRequest",
        ),
        (
            SentimentService(sentiment_provider=cast(SentimentProvider, object())),
            "SentimentSnapshotRequest",
        ),
        (
            PortfolioService(
                portfolio_provider=cast(Any, object()),
            ),
            "PortfolioAnalysisRequest",
        ),
    ],
)
async def test_service_validation_rejects_wrong_payload_without_attribute_error(
    service: Any,
    request_name: str,
) -> None:
    request = cast(
        Any,
        ServiceRequest(
            payload=object(),
            request_name=request_name,
        ),
    )

    errors = await service.validate_request(request)

    assert errors == (f"Unsupported service request: {request_name}",)


class _PartialNewsProvider:
    async def get_financial_news(
        self,
        query: str,
        sort_by: str = "publishedAt",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        raise RuntimeError("financial source unavailable")

    async def get_market_news(
        self,
        symbol: str = "SPY",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        return [
            {
                "title": "SPY market liquidity and Fed policy remain in focus",
                "description": "A deterministic stale-data fixture.",
                "source": "fixture",
                "published_at": "2020-01-01T00:00:00Z",
            }
        ]


class _FailingNewsProvider(_PartialNewsProvider):
    async def get_market_news(
        self,
        symbol: str = "SPY",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        raise RuntimeError("market source unavailable")


class _EmptyNewsProvider:
    async def get_financial_news(
        self,
        query: str,
        sort_by: str = "publishedAt",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        return []

    async def get_market_news(
        self,
        symbol: str = "SPY",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        return []


@pytest.mark.asyncio
async def test_news_service_allows_partial_source_success_and_preserves_timestamp() -> (
    None
):
    service = NewsService(
        news_provider=cast(NewsProvider, _PartialNewsProvider()),
    )

    result = await service.run(
        ServiceRequest(payload=NewsRequest()),
    )

    assert result.result is not None
    assert len(result.result.articles) == 1
    article = result.result.articles[0]
    assert article.published_at == "2020-01-01T00:00:00Z"
    assert article.relevance_score == 1.0
    assert len(result.degradations) == 1
    assert result.degradations[0].code == "provider_call_failed"
    assert result.degradations[0].component == "financial_news"
    assert result.degradations[0].error_type == "RuntimeError"


@pytest.mark.asyncio
async def test_news_service_distinguishes_empty_success_from_total_failure() -> None:
    empty_result = await NewsService(
        news_provider=cast(NewsProvider, _EmptyNewsProvider()),
    ).run(ServiceRequest(payload=NewsRequest()))

    assert empty_result.result is not None
    assert empty_result.result.articles == ()

    with pytest.raises(RuntimeError, match="All news provider calls failed"):
        await NewsService(
            news_provider=cast(NewsProvider, _FailingNewsProvider()),
        ).run(ServiceRequest(payload=NewsRequest()))


class _PartialSentimentProvider:
    async def get_fear_greed_sentiment(self) -> dict[str, Any]:
        raise RuntimeError("fear and greed unavailable")

    async def get_news_sentiment(
        self,
        symbol: str = "SPY",
    ) -> dict[str, Any]:
        return {
            "sentiment_score": 0.23751,
            "overall_sentiment": "bullish",
            "components": {
                "news": 0.23751,
                "social": 0.11111,
                "insider": -0.07123,
            },
        }


class _FailingSentimentProvider(_PartialSentimentProvider):
    async def get_news_sentiment(
        self,
        symbol: str = "SPY",
    ) -> dict[str, Any]:
        raise RuntimeError("news sentiment unavailable")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("service", "payload", "component"),
    [
        (
            NewsService(news_provider=cast(NewsProvider, _PartialNewsProvider())),
            NewsRequest(),
            "financial_news",
        ),
        (
            SentimentService(
                sentiment_provider=cast(
                    SentimentProvider,
                    _PartialSentimentProvider(),
                )
            ),
            SentimentSnapshotRequest(),
            "fear_greed",
        ),
    ],
)
async def test_partial_services_emit_one_aggregate_degradation_before_completion(
    service: Any,
    payload: Any,
    component: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sink = InMemoryTelemetrySink()
    manager = ObservabilityManager()
    manager.add_sink(sink)
    runner: ServiceRunner[Any, Any] = ServiceRunner(
        telemetry=ApplicationServiceTelemetry(observability_manager=manager),
    )

    result = await runner.run(
        service=service,
        request=ServiceRequest(payload=payload),
    )

    assert result.success is True
    assert [event.event_type for event in sink.events] == [
        "application.service.started",
        "application.service.degraded",
        "application.service.completed",
    ]
    degraded = sink.events[1]
    assert degraded.attributes["degradation_count"] == 1
    assert degraded.payload["degradations"][0]["component"] == component
    assert degraded.exception_details is None
    assert not any(
        record.name
        in {
            "application.services.news.news_service",
            "application.services.sentiment.sentiment_service",
        }
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_sentiment_service_preserves_precision_and_partial_success() -> None:
    result = await SentimentService(
        sentiment_provider=cast(SentimentProvider, _PartialSentimentProvider()),
    ).run(ServiceRequest(payload=SentimentSnapshotRequest()))

    assert result.result is not None
    assert result.result.providers["fear_greed"]["normalized_sentiment"] == 0.0
    assert len(result.degradations) == 1
    assert result.degradations[0].code == "provider_call_failed"
    assert result.degradations[0].component == "fear_greed"
    assert result.degradations[0].error_type == "RuntimeError"
    composite = result.result.composite_sentiment
    assert composite != round(composite, 4)
    assert -1.0 <= composite <= 1.0


def test_sentiment_service_reads_canonical_fear_greed_index() -> None:
    normalized = SentimentService(
        sentiment_provider=cast(SentimentProvider, object()),
    )._normalize_fear_greed(
        {"fear_greed_index": 75.25},
    )

    assert normalized["normalized_sentiment"] == pytest.approx(0.505)


@pytest.mark.asyncio
async def test_sentiment_service_raises_when_all_providers_fail() -> None:
    with pytest.raises(RuntimeError, match="All sentiment provider calls failed"):
        await SentimentService(
            sentiment_provider=cast(SentimentProvider, _FailingSentimentProvider()),
        ).run(ServiceRequest(payload=SentimentSnapshotRequest()))


def test_sentiment_analyzers_preserve_full_precision() -> None:
    features = sentiment_analysis.build_features(
        sentiment_snapshot={
            "sentiment_score": 0.23751,
            "overall_sentiment": "bullish",
            "components": {
                "news": 0.23751,
                "social": 0.11111,
                "insider": -0.07123,
            },
        }
    )
    fused = sentiment_fusion.synthesize(features=features)

    assert features["divergence"]["avg_divergence"] != round(
        features["divergence"]["avg_divergence"],
        4,
    )
    assert fused["composite_sentiment"] != round(
        fused["composite_sentiment"],
        4,
    )


class _PartialMacroProvider:
    async def get_macro_snapshot(self) -> MacroDataSnapshot:
        return MacroDataSnapshot(
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


class _FailingMacroProvider(_PartialMacroProvider):
    async def get_macro_snapshot(self) -> MacroDataSnapshot:
        raise RuntimeError("All macro provider series failed.")


@pytest.mark.asyncio
async def test_macro_service_uses_canonical_vix_key_and_partial_values() -> None:
    result = await MacroService(
        macro_provider=cast(MacroProvider, _PartialMacroProvider()),
    ).run(
        ServiceRequest(
            payload=MacroAnalysisRequest(include_raw_data=True),
        )
    )

    assert result.result is not None
    assert result.result.macro_data is not None
    assert result.result.macro_data.vix is None
    assert "vix_macro" not in result.result.macro_data.to_dict()
    assert result.result.liquidity_regime != "unknown"


@pytest.mark.asyncio
async def test_macro_service_raises_when_all_series_fail() -> None:
    with pytest.raises(RuntimeError, match="All macro provider series failed"):
        await MacroService(
            macro_provider=cast(MacroProvider, _FailingMacroProvider()),
        ).run(ServiceRequest(payload=MacroAnalysisRequest()))


class _CanonicalMarketEventsProvider:
    async def get_economic_events(
        self,
        days_ahead: int = 14,
    ) -> list[dict[str, Any]]:
        return [
            {
                "name": "CPI Release",
                "timestamp": "2026-07-01T12:30:00+00:00",
                "symbol": "SPY",
                "impact": 0.95,
                "direction_bias": "neutral",
                "source": "fred_events",
            }
        ]

    async def get_fed_events(
        self,
        days_ahead: int = 14,
    ) -> list[dict[str, Any]]:
        return [
            {
                "name": "Fed Chair Speech",
                "timestamp": "2026-07-02T14:00:00+00:00",
                "symbol": "SPY",
                "impact": 0.85,
                "direction_bias": "neutral",
                "source": "fed_events",
            }
        ]

    async def get_earnings_events(
        self,
        horizon: str = "3month",
        symbols: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        return [
            {
                "symbol": "AAPL",
                "company": "Apple Inc.",
                "report_date": "2026-07-30T20:00:00+00:00",
            }
        ]


@pytest.mark.asyncio
async def test_market_events_service_preserves_canonical_provider_timestamps() -> None:
    result = await MarketEventsService(
        events_provider=cast(MarketEventsProvider, _CanonicalMarketEventsProvider()),
    ).run(ServiceRequest(payload=MarketEventsRequest()))

    assert result.result is not None
    timestamps = {event["timestamp"] for event in result.result.events}
    assert timestamps == {
        "2026-07-01T12:30:00+00:00",
        "2026-07-02T14:00:00+00:00",
        "2026-07-30T20:00:00+00:00",
    }


def test_market_event_pressure_preserves_precision_and_numeric_volatility() -> None:
    service = MarketEventsService(
        events_provider=cast(MarketEventsProvider, object()),
    )
    pressure = service._aggregate_pressure(
        [
            {"impact_score": 1.0 / 3.0, "direction_bias": "bullish"},
            {"impact_score": 2.0 / 7.0, "direction_bias": "bearish"},
            {"impact_score": 0.91, "direction_bias": "neutral"},
        ]
    )

    expected = ((1.0 / 3.0 + 2.0 / 7.0 + 0.91) / 3.0) * 0.3
    assert pressure["pressure_score"] == pytest.approx(expected)
    assert pressure["volatility_pressure"] == pressure["pressure_score"]
    assert pressure["pressure_score"] != round(
        pressure["pressure_score"],
        4,
    )


class _FailingTechnicalProvider:
    async def get_symbol_data(self, symbol: str, days: int) -> Any:
        raise RuntimeError("market data unavailable")


@pytest.mark.asyncio
async def test_technical_service_propagates_provider_failure() -> None:
    with pytest.raises(RuntimeError, match="market data unavailable"):
        await TechnicalAnalysisService(
            data_provider=cast(Any, _FailingTechnicalProvider()),
        ).run(ServiceRequest(payload=TechnicalAnalysisRequest()))


class _FailingPortfolioProvider:
    async def get_account(self) -> dict[str, Any]:
        raise RuntimeError("portfolio unavailable")


@pytest.mark.asyncio
async def test_portfolio_service_propagates_provider_failure() -> None:
    with pytest.raises(RuntimeError, match="portfolio unavailable"):
        await PortfolioService(
            portfolio_provider=cast(Any, _FailingPortfolioProvider()),
        ).run(ServiceRequest(payload=PortfolioAnalysisRequest()))


class _NeutralSentimentRunner:
    async def run(
        self,
        *,
        service: object,
        request: object,
    ) -> ServiceResult[SentimentSnapshotResult]:
        request_id = str(getattr(request, "request_id", "request-1"))
        sentiment = {
            "composite_sentiment": 0.0,
            "confidence": 0.8,
            "regime": "neutral",
        }
        return ServiceResult.ok(
            request_id=request_id,
            request_name="SentimentSnapshotRequest",
            result=SentimentSnapshotResult(
                symbol="SPY",
                providers={},
                features={
                    "momentum": 0.0,
                    "stability": 1.0,
                    "divergence": {},
                    "risk_multiplier": 1.0,
                    "components": {},
                },
                sentiment=sentiment,
                composite_sentiment=0.0,
                market_regime="neutral",
                market_bias="neutral",
                confidence=0.8,
            ),
        )


class _NeutralLLM:
    async def chat(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "summary": "Neutral sentiment.",
            "sentiment_bias": "neutral",
            "fear_greed_state": "neutral",
            "positioning_state": "balanced",
            "confidence": 0.8,
            "risks": [],
            "recommendations": [],
        }


class _Telemetry:
    async def emit_agent_signal(self, **kwargs: Any) -> None:
        return None


@pytest.mark.asyncio
async def test_sentiment_agent_does_not_remap_native_minus_one_to_one_score() -> None:
    agent = SentimentAgent(
        sentiment_service=cast(SentimentService, object()),
        llm_service=cast(LLMService, _NeutralLLM()),
        service_runner=cast(ServiceRunner[Any, Any], _NeutralSentimentRunner()),
        intelligence_telemetry=cast(IntelligenceTelemetry, _Telemetry()),
    )

    output = await agent._execute(
        RuntimeContext(
            runtime_id="runtime-1",
            workflow_id="morning_report",
            execution_id="execution-1",
            workflow_inputs={"symbol": "SPY"},
        )
    )

    assert output.outputs["directional_score"] == 0.0
    assert output.outputs["regime"] == "neutral"
