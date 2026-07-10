from __future__ import annotations

from typing import Any, Dict, List
from typing import TYPE_CHECKING

from application.services.base import ServiceRequest
from application.services.base import ServiceResult
from application.services.base.application_service import (
    ApplicationService,
    ValidatingApplicationService,
)

from application.services.market_events.market_events_request import (
    MarketEventsRequest,
)
from application.services.market_events.market_events_result import (
    MarketEventsResult,
)
from application.services.market_events import earnings_clusters
from application.services.market_events import event_scoring

if TYPE_CHECKING:
    from integration.providers.market_events.market_events_provider import (
        MarketEventsProvider,
    )


class MarketEventsService(ApplicationService, ValidatingApplicationService):
    """
    Polaris Market Events Intelligence Service (EVENT FUSION LAYER)

    ROLE:
    -----
    This is the SINGLE ENTRY POINT for all market-moving events.

    It:
    - aggregates macro + micro events
    - normalizes schema across sources
    - applies event impact scoring
    - produces forward-looking market pressure signals

    CONSUMERS:
    ----------
    - StrategySynthesisAgent  (PRIMARY)
    - StrategyPerspectiveWeightingEngine
    - RiskAggregatorAgent
    """

    service_name = "market_events_service"

    def __init__(
        self,
        events_provider: MarketEventsProvider,
    ) -> None:

        self.events_provider = events_provider

    async def run(
        self,
        request: ServiceRequest[MarketEventsRequest],
    ) -> ServiceResult[MarketEventsResult]:
        result = await self._execute(
            request.payload,
        )

        return ServiceResult.ok(
            request_id=request.request_id,
            request_name=request.request_name,
            result=result,
        )

    async def validate_request(
        self,
        request: ServiceRequest[MarketEventsRequest],
    ) -> tuple[str, ...]:
        errors: list[str] = []

        if not isinstance(request.payload, MarketEventsRequest):
            return (f"Unsupported service request: {request.request_name}",)

        if not request.payload.symbol.strip():
            errors.append(
                "symbol is required.",
            )

        if request.payload.lookahead_days < 0:
            errors.append(
                "lookahead_days cannot be negative.",
            )

        if not request.payload.horizon.strip():
            errors.append(
                "horizon is required.",
            )

        if (
            not request.payload.symbol_constituents
            or len(request.payload.symbol_constituents) == 0
        ):
            errors.append(
                "symbol_constituents is required.",
            )

        return tuple(errors)

    # ============================================================
    # MAIN ENTRY POINT
    # ============================================================

    async def _execute(
        self,
        request: MarketEventsRequest,
    ) -> MarketEventsResult:
        """
        Unified market event intelligence snapshot.
        """

        symbol = request.symbol
        lookahead_days = request.lookahead_days
        horizon = request.horizon
        symbol_constituents = set(request.symbol_constituents)

        # ========================================================
        # COLLECT RAW EVENTS
        # ========================================================

        macro_events = await self.events_provider.get_economic_events(
            days_ahead=lookahead_days,
        )

        fed_events = await self.events_provider.get_fed_events(
            days_ahead=lookahead_days,
        )

        earnings_events = await self.events_provider.get_earnings_events(
            horizon=horizon,
            symbols=symbol_constituents,
        )

        earnings_events = earnings_clusters.get_clusters(events=earnings_events)

        # ========================================================
        # NORMALIZE EVENTS
        # ========================================================

        normalized_events = []

        normalized_events.extend(self._normalize_macro_events(macro_events))

        normalized_events.extend(self._normalize_fed_events(fed_events))

        normalized_events.extend(self._normalize_earnings_events(earnings_events))

        # ========================================================
        # SCORE EVENTS
        # ========================================================

        scored_events = [
            event_scoring.score_event(event) for event in normalized_events
        ]

        # ========================================================
        # AGGREGATE MARKET PRESSURE
        # ========================================================

        pressure_state = self._aggregate_pressure(scored_events)

        # ========================================================
        # EXTRACT HIGH IMPACT EVENTS
        # ========================================================

        high_impact_events = [
            e for e in scored_events if e.get("impact_score", 0) >= 0.7
        ]

        # ========================================================
        # FINAL OUTPUT CONTRACT
        # ========================================================

        return MarketEventsResult(
            symbol=symbol,
            market_pressure_score=pressure_state["pressure_score"],
            volatility_pressure=pressure_state["volatility_pressure"],
            volatility_forecast=pressure_state["volatility"],
            regime_bias=pressure_state["regime_bias"],
            events=tuple(scored_events),
            high_impact_events=tuple(high_impact_events),
            event_count=len(scored_events),
            high_impact_count=len(high_impact_events),
            risk_projection={
                "expected_volatility": pressure_state["volatility"],
                "volatility_pressure": pressure_state["volatility_pressure"],
                "event_density": pressure_state["event_density"],
                "directional_bias": pressure_state["regime_bias"],
            },
        )

    # ============================================================
    # NORMALIZATION LAYERS
    # ============================================================

    def _normalize_macro_events(
        self,
        events: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        return [
            {
                **event,
                "event_type": "macro",
                "name": event.get("name"),
                "timestamp": event.get("timestamp"),
                "symbol": event.get("symbol", "SPY"),
                "expected_impact": event.get("impact", 0.5),
                "direction_bias": event.get("direction_bias", "neutral"),
                "source": event.get("source", "fred_events"),
            }
            for event in events
        ]

    def _normalize_fed_events(
        self,
        events: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        return [
            {
                **event,
                "event_type": "fed",
                "name": event.get("name"),
                "timestamp": event.get("timestamp"),
                "symbol": event.get("symbol", "SPY"),
                "expected_impact": event.get("impact", 0.8),
                "direction_bias": event.get("direction_bias", "neutral"),
                "source": event.get("source", "fed_events"),
            }
            for event in events
        ]

    def _normalize_earnings_events(
        self,
        events: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        return [
            {
                **event,
                "event_type": "earnings",
                "name": event.get("company"),
                "timestamp": event.get("timestamp"),
                "symbol": event.get("symbol"),
                "expected_impact": event.get("volatility_score", 0.6),
                "direction_bias": "neutral",
                "source": "earnings_events",
            }
            for event in events
        ]

    # ============================================================
    # MARKET PRESSURE AGGREGATION
    # ============================================================

    def _aggregate_pressure(
        self,
        events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        if not events:
            return {
                "pressure_score": 0.0,
                "volatility_pressure": 0.0,
                "volatility": "low",
                "regime_bias": "neutral",
                "event_density": 0.0,
            }

        total_impact = sum(e.get("impact_score", 0.0) for e in events)

        avg_impact = total_impact / len(events)

        # event density = how crowded the calendar is
        event_density = min(len(events) / 10.0, 1.0)

        # volatility projection
        volatility_score = avg_impact * event_density

        if volatility_score >= 0.7:
            volatility = "high"
        elif volatility_score >= 0.4:
            volatility = "medium"
        else:
            volatility = "low"

        # directional bias inference
        bullish = sum(1 for e in events if e.get("direction_bias") == "bullish")

        bearish = sum(1 for e in events if e.get("direction_bias") == "bearish")

        if bullish > bearish:
            regime_bias = "risk_on"
        elif bearish > bullish:
            regime_bias = "risk_off"
        else:
            regime_bias = "neutral"

        return {
            "pressure_score": volatility_score,
            "volatility_pressure": volatility_score,
            "volatility": volatility,
            "regime_bias": regime_bias,
            "event_density": event_density,
        }
