from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import cast

import pytest

from application.services.base import ServiceResult
from application.services.base import ServiceRunner
from application.services.news.news_service import NewsService
from application.services.news.news_result import NewsArticle
from application.services.news.news_result import NewsResult
from application.services.sentiment.sentiment_result import SentimentSnapshotResult
from application.services.sentiment.sentiment_service import SentimentService
from core.llm.llm_service import LLMService
from core.runtime.state.runtime_context import RuntimeContext
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from domain.workflow_outputs import NEWS_ANALYSIS_OUTPUT_CONTRACT
from domain.workflow_outputs import SENTIMENT_SNAPSHOT_OUTPUT_CONTRACT
from intelligence.research.news.news_agent import NewsAgent
from intelligence.research.sentiment.sentiment_agent import SentimentAgent


@pytest.mark.asyncio
async def test_news_agent_emits_first_class_projection_fields() -> None:
    agent = NewsAgent(
        news_service=cast(NewsService, object()),
        llm_service=cast(LLMService, _NewsLLM()),
        service_runner=cast(ServiceRunner[Any, Any], _NewsRunner()),
        intelligence_telemetry=cast(IntelligenceTelemetry, _Telemetry()),
    )

    output = await agent._execute(
        RuntimeContext(
            runtime_id="runtime-1",
            workflow_id="morning_report",
            execution_id="exec-1",
            workflow_inputs={"symbol": "SPY", "query": "SPY OR Fed"},
        )
    )

    assert output.output_contract == NEWS_ANALYSIS_OUTPUT_CONTRACT
    assert isinstance(
        datetime.fromisoformat(str(output.outputs["observed_at"])), datetime
    )
    assert output.outputs["news_source"] == "NewsService"
    assert output.outputs["symbol"] == "SPY"
    assert output.outputs["query"] == "SPY OR Fed"
    assert output.outputs["news_articles"] == output.outputs["features"]["articles"]
    assert output.outputs["news_articles"][0]["id"] == "article-1"


@pytest.mark.asyncio
async def test_sentiment_agent_emits_first_class_projection_fields() -> None:
    agent = SentimentAgent(
        sentiment_service=cast(SentimentService, object()),
        llm_service=cast(LLMService, _SentimentLLM()),
        service_runner=cast(ServiceRunner[Any, Any], _SentimentRunner()),
        intelligence_telemetry=cast(IntelligenceTelemetry, _Telemetry()),
    )

    output = await agent._execute(
        RuntimeContext(
            runtime_id="runtime-1",
            workflow_id="morning_report",
            execution_id="exec-1",
            workflow_inputs={"symbol": "SPY"},
        )
    )

    assert output.output_contract == SENTIMENT_SNAPSHOT_OUTPUT_CONTRACT
    assert isinstance(
        datetime.fromisoformat(str(output.outputs["observed_at"])), datetime
    )
    assert output.outputs["sentiment_source"] == "SentimentService"
    assert output.outputs["sentiment_universe"] == "single_symbol"
    assert output.outputs["symbol"] == "SPY"
    assert output.outputs["sentiment_snapshot"]["composite_sentiment"] == 0.35
    assert output.outputs["sentiment_source_data"]["providers"]["fear_greed"][
        "timestamp"
    ]


class _NewsRunner:
    async def run(
        self,
        *,
        service: object,
        request: object,
    ) -> ServiceResult[NewsResult]:
        return ServiceResult.ok(
            request_id=str(getattr(request, "request_id", "request-1")),
            request_name="NewsRequest",
            result=NewsResult(
                articles=(
                    NewsArticle(
                        article_id="article-1",
                        title="Fed signals policy patience",
                        summary="Officials emphasized data dependence.",
                        source="Reuters",
                        url="https://example.test/fed-policy",
                        published_at="2026-07-10T12:00:00+00:00",
                        headline_score=0.8,
                        relevance_score=0.9,
                        sentiment_hint=0.25,
                        raw={"vendor_id": "article-1"},
                    ),
                ),
            ),
        )


class _SentimentRunner:
    async def run(
        self,
        *,
        service: object,
        request: object,
    ) -> ServiceResult[SentimentSnapshotResult]:
        return ServiceResult.ok(
            request_id=str(getattr(request, "request_id", "request-1")),
            request_name="SentimentSnapshotRequest",
            result=SentimentSnapshotResult(
                symbol="SPY",
                providers={
                    "fear_greed": {
                        "timestamp": "2026-07-10T12:45:00+00:00",
                        "normalized_sentiment": 0.28,
                    }
                },
                features={
                    "stability": 0.66,
                    "momentum": 0.12,
                    "divergence": 0.08,
                    "risk_multiplier": 1.1,
                    "components": {
                        "news": 0.4,
                        "social": 0.2,
                        "fear_greed": 0.64,
                    },
                },
                sentiment={
                    "composite_sentiment": 0.35,
                    "confidence": 0.72,
                    "regime": "bullish",
                    "market_bias": "risk_on",
                },
                composite_sentiment=0.35,
                market_regime="bullish",
                market_bias="risk_on",
                confidence=0.72,
            ),
        )


class _NewsLLM:
    def chat(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "summary": "Policy expectations remain constructive.",
            "market_relevance": "bullish",
            "themes": ["fed_policy", "rates"],
            "signals": ["liquidity_support"],
            "risks": ["event_risk"],
            "recommendations": ["monitor_rates"],
        }


class _SentimentLLM:
    def chat(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "summary": "Sentiment is constructive.",
            "sentiment_bias": "risk_on",
            "fear_greed_state": "greed",
            "positioning_state": "balanced",
            "confidence": 0.72,
            "risks": [],
            "recommendations": [],
        }


class _Telemetry:
    async def emit_agent_signal(self, **kwargs: Any) -> None:
        return None

    async def emit_agent_degraded(self, **kwargs: Any) -> None:
        return None
