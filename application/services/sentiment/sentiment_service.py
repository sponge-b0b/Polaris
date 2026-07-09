from __future__ import annotations

import asyncio
from typing import Any, Dict
from typing import TYPE_CHECKING

from application.services.base import ServiceDegradation
from application.services.base import ServiceRequest
from application.services.base import ServiceResult
from application.services.base.application_service import (
    ApplicationService,
    ValidatingApplicationService,
)

from application.services.sentiment.sentiment_request import (
    SentimentSnapshotRequest,
)
from application.services.sentiment.sentiment_result import (
    SentimentSnapshotResult,
)
from application.services.sentiment import sentiment_analysis
from application.services.sentiment import sentiment_fusion

if TYPE_CHECKING:
    from integration.providers.sentiment.sentiment_provider import (
        SentimentProvider,
    )


class SentimentService(ApplicationService, ValidatingApplicationService):
    """
    Polaris Sentiment Service (Production SAFE v2)

    ENFORCES:
    - -1 → +1 normalization boundary
    - provider isolation
    - deterministic fusion pipeline
    """

    service_name = "sentiment_service"

    def __init__(
        self,
        sentiment_provider: SentimentProvider,
    ) -> None:

        self.sentiment_provider = sentiment_provider

    async def run(
        self,
        request: ServiceRequest[SentimentSnapshotRequest],
    ) -> ServiceResult[SentimentSnapshotResult]:
        result, degradations = await self._execute_with_degradations(
            request.payload,
        )

        return ServiceResult.ok(
            request_id=request.request_id,
            request_name=request.request_name,
            result=result,
            degradations=degradations,
        )

    async def validate_request(
        self,
        request: ServiceRequest[SentimentSnapshotRequest],
    ) -> tuple[str, ...]:
        errors: list[str] = []

        if not isinstance(request.payload, SentimentSnapshotRequest):
            return (f"Unsupported service request: {request.request_name}",)

        if not request.payload.symbol.strip():
            errors.append(
                "symbol is required.",
            )

        return tuple(errors)

    # ============================================================
    # MAIN ENTRY
    # ============================================================

    async def _execute(
        self,
        request: SentimentSnapshotRequest,
    ) -> SentimentSnapshotResult:
        result, _ = await self._execute_with_degradations(request)
        return result

    async def _execute_with_degradations(
        self,
        request: SentimentSnapshotRequest,
    ) -> tuple[SentimentSnapshotResult, tuple[ServiceDegradation, ...]]:

        symbol = request.symbol
        previous_snapshot = request.previous_snapshot
        risk_state = request.risk_state

        # ========================================================
        # PROVIDER INGESTION (SAFE WRAPPED)
        # ========================================================

        provider_results = await asyncio.gather(
            self.sentiment_provider.get_fear_greed_sentiment(),
            self.sentiment_provider.get_news_sentiment(symbol=symbol),
            return_exceptions=True,
        )

        provider_data: dict[str, dict[str, Any]] = {}
        degradations: list[ServiceDegradation] = []
        for provider_name, provider_result in zip(
            ("fear_greed", "news_sentiment"),
            provider_results,
        ):
            if isinstance(provider_result, BaseException):
                if isinstance(provider_result, asyncio.CancelledError):
                    raise provider_result
                provider_data[provider_name] = {}
                degradations.append(
                    ServiceDegradation(
                        code="provider_call_failed",
                        component=provider_name,
                        summary=(
                            "Sentiment provider call failed; the service completed "
                            "with remaining provider data."
                        ),
                        error_type=type(provider_result).__name__,
                    )
                )
                continue

            if not isinstance(provider_result, dict):
                provider_data[provider_name] = {}
                degradations.append(
                    ServiceDegradation(
                        code="invalid_provider_payload",
                        component=provider_name,
                        summary=(
                            "Sentiment provider returned an invalid payload; the "
                            "service completed with remaining provider data."
                        ),
                        error_type="InvalidProviderPayload",
                    )
                )
                continue

            provider_data[provider_name] = provider_result

        if len(degradations) == len(provider_results):
            raise RuntimeError("All sentiment provider calls failed.")

        fear_greed_raw = provider_data["fear_greed"]
        provider_sentiment = provider_data["news_sentiment"]

        fear_greed_normalized = self._normalize_fear_greed(fear_greed_raw)

        # ========================================================
        # MERGE PROVIDER CONTEXT
        # ========================================================

        sentiment_snapshot = {
            **provider_sentiment,
            "fear_greed": fear_greed_normalized,
        }

        # ========================================================
        # FEATURE ENGINEERING LAYER
        # ========================================================

        features = sentiment_analysis.build_features(
            sentiment_snapshot=sentiment_snapshot,
            previous_snapshot=previous_snapshot,
            risk_state=risk_state,
        )

        # ========================================================
        # FUSION LAYER
        # ========================================================

        fused_sentiment = sentiment_fusion.synthesize(
            features=features,
        )

        # ========================================================
        # FINAL OUTPUT
        # ========================================================

        return (
            SentimentSnapshotResult(
                symbol=symbol,
                providers={
                    "alpha_vantage": provider_sentiment,
                    "fear_greed": fear_greed_normalized,
                },
                features=features,
                sentiment=fused_sentiment,
                composite_sentiment=float(
                    fused_sentiment.get("composite_sentiment", 0.0)
                ),
                market_regime=str(fused_sentiment.get("regime", "neutral")),
                market_bias=str(fused_sentiment.get("market_bias", "neutral")),
                confidence=float(fused_sentiment.get("confidence", 0.0)),
            ),
            tuple(degradations),
        )

    # ============================================================
    # FEAR & GREED NORMALIZATION (-1 → +1)
    # ============================================================

    def _normalize_fear_greed(self, fg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Converts Fear & Greed index into normalized sentiment space.
        Assumes typical 0–100 scale.
        """

        value = fg.get(
            "fear_greed_index",
            fg.get("value", fg.get("fear_greed", 50)),
        )

        try:
            value = float(value)
        except (TypeError, ValueError):
            value = 50.0

        # normalize 0–100 → -1 to +1
        normalized = (value - 50.0) / 50.0
        normalized = max(-1.0, min(1.0, normalized))

        return {
            **fg,
            "normalized_sentiment": normalized,
        }
