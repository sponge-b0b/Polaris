from typing import Protocol, Dict, Any, runtime_checkable


@runtime_checkable
class SentimentProvider(Protocol):
    """
    Canonical sentiment provider interface.

    ALL sentiment providers MUST implement this interface.
    """

    async def get_news_sentiment(
        self,
        symbol: str = "SPY",
    ) -> Dict[str, Any]: ...

    async def get_fear_greed_sentiment(
        self,
    ) -> Dict[str, Any]: ...
