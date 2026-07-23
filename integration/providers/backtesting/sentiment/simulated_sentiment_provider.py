from typing import Any

from integration.providers.sentiment.sentiment_provider import SentimentProvider


class SimulatedSentimentProvider(SentimentProvider):
    def __init__(
        self,
    ) -> None:
        pass

    async def get_news_sentiment(
        self,
        symbol: str = "SPY",
    ) -> dict[str, Any]:

        return {}

    async def get_fear_greed_sentiment(
        self,
    ) -> dict[str, Any]:

        return {}
