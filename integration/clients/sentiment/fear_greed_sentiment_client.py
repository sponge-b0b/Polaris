from __future__ import annotations

import httpx
from typing import Any, Dict, Optional


class FearGreedSentimentClient:
    """
    CNN Fear & Greed Index Client.

    Purpose:
    - fetch Fear & Greed Index
    - normalize market sentiment regime
    - provide emotional market state

    NOTE:
    CNN does not provide an official public API.
    This implementation uses the public endpoint
    currently exposed by CNN.

    If CNN changes the endpoint later,
    only this provider needs updating.
    """

    BASE_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"

    def __init__(
        self,
        timeout: int = 10,
    ) -> None:

        self.timeout = timeout

    # ============================================================
    # HIGH-LEVEL SENTIMENT SNAPSHOT
    # ============================================================

    async def get_fear_greed_sentiment(
        self,
        client: Optional[httpx.AsyncClient] = None,
    ) -> Dict[str, Any]:

        if client is not None:
            current = await self.get_current_index(client)
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                current = await self.get_current_index(client)

        score = current.get(
            "score",
            50,
        )

        regime = current.get(
            "sentiment_regime",
            "neutral",
        )

        risk_bias = self._risk_bias(regime)

        return {
            "fear_greed_index": score,
            "market_emotion": regime,
            "risk_bias": risk_bias,
            "rating": current.get(
                "rating",
                "Neutral",
            ),
        }

    # ============================================================
    # CURRENT FEAR & GREED
    # ============================================================

    async def get_current_index(
        self,
        client: Optional[httpx.AsyncClient] = None,
    ) -> Dict[str, Any]:
        """
        Fetch current Fear & Greed index.
        """

        if client is not None:
            data = await self._get_raw_data(client)
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as owned_client:
                data = await self._get_raw_data(owned_client)

        fg = data.get("fear_and_greed", {})
        score = fg.get("score", 50)
        rating = fg.get("rating", "Neutral")
        return {
            "score": score,
            "rating": rating,
            "sentiment_regime": self._normalize_regime(score),
            "previous_close": fg.get("previous_close"),
            "previous_week": fg.get("previous_1_week"),
            "previous_month": fg.get("previous_1_month"),
            "previous_year": fg.get("previous_1_year"),
        }

    # ============================================================
    # FETCH RAW DATA
    # ============================================================

    async def _get_raw_data(self, client: httpx.AsyncClient) -> Dict[str, Any]:

        response = await client.get(
            self.BASE_URL,
            timeout=self.timeout,
        )

        response.raise_for_status()
        return response.json()

    # ============================================================
    # MARKET EMOTIONAL REGIME
    # ============================================================

    def _normalize_regime(
        self,
        score: float,
    ) -> str:

        if score >= 75:
            return "extreme_greed"

        elif score >= 60:
            return "greed"

        elif score >= 45:
            return "neutral"

        elif score >= 25:
            return "fear"

        return "extreme_fear"

    # ============================================================
    # RISK BIAS MAPPING
    # ============================================================

    def _risk_bias(
        self,
        regime: str,
    ) -> str:

        if regime in [
            "extreme_greed",
            "greed",
        ]:
            return "risk_on"

        if regime in [
            "fear",
            "extreme_fear",
        ]:
            return "risk_off"

        return "neutral"
