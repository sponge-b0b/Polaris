from typing import Any

from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.clients.sentiment.alphavantage_sentiment_client import (
    AlphaVantageSentimentClient,
)
from integration.clients.sentiment.fear_greed_sentiment_client import (
    FearGreedSentimentClient,
)
from integration.providers.provider_telemetry import record_provider_call
from integration.providers.sentiment.sentiment_provider import SentimentProvider


class LiveSentimentProvider(SentimentProvider):
    def __init__(
        self,
        alphavantage_sentiment_client: AlphaVantageSentimentClient,
        fear_greed_sentiment_client: FearGreedSentimentClient,
        telemetry: IntegrationTelemetry | None = None,
    ) -> None:

        self.alphavantage_sentiment_client = alphavantage_sentiment_client
        self.fear_greed_sentiment_client = fear_greed_sentiment_client
        self.telemetry = telemetry

    async def get_news_sentiment(
        self,
        symbol: str = "SPY",
    ) -> dict[str, Any]:

        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_news_sentiment",
            lambda: self.alphavantage_sentiment_client.get_news_sentiment(
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
            self.fear_greed_sentiment_client.get_fear_greed_sentiment,
        )
