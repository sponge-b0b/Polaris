from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SentimentProvider(Protocol):
    """
    Canonical sentiment provider interface.

    ALL sentiment providers MUST implement this interface.
    """

    async def get_news_sentiment(
        self,
        symbol: str = "SPY",
    ) -> dict[str, Any]: ...

    async def get_fear_greed_sentiment(
        self,
    ) -> dict[str, Any]: ...
