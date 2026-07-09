from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest

from config.settings import Settings
from integration.clients.market_events.alphavantage_events_client import (
    AlphaVantageEarningsClient,
)
from integration.clients.market_events.fed_events_client import FedEventsClient
from integration.clients.market_events.fred_events_client import FredEventsClient
from integration.clients.news.finnhub_news_client import FinnhubNewsClient
from integration.clients.news.newsapi_news_client import NewsApiNewsClient
from integration.clients.sentiment.alphavantage_sentiment_client import (
    AlphaVantageSentimentClient,
)
from integration.clients.sentiment.fear_greed_sentiment_client import (
    FearGreedSentimentClient,
)


def _settings(**values: str) -> Settings:
    return cast(Settings, SimpleNamespace(**values))


class _JsonResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class _SentimentHttpClient:
    async def get(self, *args: Any, **kwargs: Any) -> _JsonResponse:
        return _JsonResponse(
            {
                "feed": [
                    {
                        "title": "Precise sentiment fixture",
                        "ticker_sentiment": [
                            {
                                "ticker": "SPY",
                                "ticker_sentiment_score": "0.237519",
                                "relevance_score": "0.713337",
                            }
                        ],
                    }
                ]
            }
        )


class _FailingHttpClient:
    async def get(self, *args: Any, **kwargs: Any) -> _JsonResponse:
        raise RuntimeError("transport unavailable")


def test_earnings_csv_does_not_prepend_a_synthetic_empty_event() -> None:
    client = AlphaVantageEarningsClient(_settings(ALPHAVANTAGE_API_KEY="test-key"))

    events = client._parse_csv(
        "symbol,name,reportDate,fiscalDateEnding,estimate,currency\n"
        "AAPL,Apple Inc.,2026-07-30,2026-06-30,1.25,USD\n",
        symbols={"AAPL"},
    )

    assert len(events) == 1
    assert events[0]["symbol"] == "AAPL"
    assert events[0]["report_date"] == datetime(2026, 7, 30)


@pytest.mark.asyncio
async def test_alpha_vantage_sentiment_preserves_full_precision() -> None:
    client = AlphaVantageSentimentClient(_settings(ALPHAVANTAGE_API_KEY="test-key"))

    result = await client.get_news_sentiment(
        symbol="SPY",
        client=cast(Any, _SentimentHttpClient()),
    )

    assert result["sentiment_score"] != round(result["sentiment_score"], 4)
    assert result["confidence_score"] != round(result["confidence_score"], 4)
    assert result["components"]["news"] == result["sentiment_score"]


@pytest.mark.asyncio
async def test_newsapi_and_fear_greed_transport_failures_are_not_hidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    news_client = NewsApiNewsClient(_settings(NEWSAPI_API_KEY="test-key"))

    def fail_newsapi(**kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("newsapi unavailable")

    monkeypatch.setattr(news_client.client, "get_everything", fail_newsapi)

    with pytest.raises(RuntimeError, match="newsapi unavailable"):
        await news_client.get_financial_news(query="markets")

    with pytest.raises(RuntimeError, match="transport unavailable"):
        await FearGreedSentimentClient().get_current_index(
            client=cast(Any, _FailingHttpClient())
        )


@pytest.mark.asyncio
async def test_finnhub_all_news_allows_partial_success_and_propagates_cancellation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FinnhubNewsClient(_settings(FINNHUB_API_KEY="test-key"))

    async def fail_company(**kwargs: Any) -> list[dict[str, Any]]:
        raise RuntimeError("company news unavailable")

    async def market_news(**kwargs: Any) -> list[dict[str, Any]]:
        return [{"headline": "Market fixture"}]

    monkeypatch.setattr(client, "get_company_news", fail_company)
    monkeypatch.setattr(client, "get_market_news", market_news)

    assert await client.get_all_news(client=cast(Any, object())) == [
        {"headline": "Market fixture"}
    ]

    async def cancel_company(**kwargs: Any) -> list[dict[str, Any]]:
        raise asyncio.CancelledError

    monkeypatch.setattr(client, "get_company_news", cancel_company)
    with pytest.raises(asyncio.CancelledError):
        await client.get_all_news(client=cast(Any, object()))


@pytest.mark.asyncio
async def test_fed_and_fred_clients_allow_partial_sources_but_raise_on_total_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fed_client = FedEventsClient()

    async def partial_fed_fetch(*, url: str, client: Any) -> str:
        del client
        if "fomccalendars" in url:
            raise RuntimeError("calendar unavailable")
        if "newsevents" in url:
            return "<html></html>"
        return "<rss><channel></channel></rss>"

    monkeypatch.setattr(fed_client, "_get_events", partial_fed_fetch)
    assert await fed_client.get_fed_events() == []

    async def fail_fed_fetch(*, url: str, client: Any) -> str:
        del url, client
        raise RuntimeError("fed unavailable")

    monkeypatch.setattr(fed_client, "_get_events", fail_fed_fetch)
    with pytest.raises(RuntimeError, match="All Federal Reserve event sources failed"):
        await fed_client.get_fed_events()

    fred_client = FredEventsClient(_settings(FRED_API_KEY="test-key"))
    future_date = (datetime.now(UTC) + timedelta(days=1)).date().isoformat()

    async def partial_fred_fetch(
        release_id: int,
        client: Any,
    ) -> list[dict[str, Any]]:
        del client
        if release_id == 10:
            return [{"date": future_date}]
        raise RuntimeError("release unavailable")

    monkeypatch.setattr(fred_client, "_get_release_dates", partial_fred_fetch)
    events = await fred_client.get_economic_events(days_ahead=2)
    assert len(events) == 1
    assert events[0]["name"] == "CPI Release"

    async def fail_fred_fetch(
        release_id: int,
        client: Any,
    ) -> list[dict[str, Any]]:
        del release_id, client
        raise RuntimeError("fred unavailable")

    monkeypatch.setattr(fred_client, "_get_release_dates", fail_fred_fetch)
    with pytest.raises(RuntimeError, match="All FRED release sources failed"):
        await fred_client.get_economic_events()
