from typing import Any

from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.providers.backtesting.sentiment.simulated_sentiment_provider import (
    SimulatedSentimentProvider,
)
from integration.providers.provider_telemetry import record_provider_call
from integration.providers.sentiment.sentiment_provider import SentimentProvider


class BacktestSentimentProvider(SentimentProvider):
    def __init__(
        self,
        sentiment_provider: SimulatedSentimentProvider,
        telemetry: IntegrationTelemetry | None = None,
    ) -> None:

        self.sentiment_provider = sentiment_provider
        self.telemetry = telemetry

    async def get_news_sentiment(
        self,
        symbol: str = "SPY",
    ) -> dict[str, Any]:

        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_news_sentiment",
            lambda: self.sentiment_provider.get_news_sentiment(
                symbol=symbol,
            ),
        )

    async def get_fear_greed_sentiment(
        self,
    ) -> dict[str, Any]:

        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_fear_greed_sentiment",
            self.sentiment_provider.get_fear_greed_sentiment,
        )
