from typing import Any

from dishka import Provider, Scope, provide

from application.services.base import ServiceRunner
from application.services.market_events.market_events_service import (
    MarketEventsService,
)
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from intelligence.strategy.bear.bear_agent import BearAgent
from intelligence.strategy.bull.bull_agent import BullAgent
from intelligence.strategy.sideways.sideways_agent import SidewaysAgent
from intelligence.strategy.hypothesis.evidence_builder import (
    StrategyEvidenceBuilder,
)
from intelligence.strategy.synthesis.strategy_synthesis_agent import (
    StrategySynthesisAgent,
)
from intelligence.strategy.weighting.adaptive_weighting_engine import (
    AdaptiveStrategyWeightingEngine,
)


class IntelligenceStrategyDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # Bear Agent
    @provide
    def provide_bear_agent(
        self,
    ) -> BearAgent:

        return BearAgent()

    # Bull Agent
    @provide
    def provide_bull_agent(
        self,
    ) -> BullAgent:

        return BullAgent()

    # Sideways Agent
    @provide
    def provide_sideways_agent(
        self,
    ) -> SidewaysAgent:

        return SidewaysAgent()

    # Synthesis Agent
    @provide
    def provide_synthesis_agent(
        self,
        events_service: MarketEventsService,
        service_runner: ServiceRunner[Any, Any],
        intelligence_telemetry: IntelligenceTelemetry,
    ) -> StrategySynthesisAgent:

        return StrategySynthesisAgent(
            events_service=events_service,
            service_runner=service_runner,
            intelligence_telemetry=intelligence_telemetry,
        )

    # Strategy Evidence Builder
    @provide
    def provide_strategy_evidence_builder(
        self,
        events_service: MarketEventsService,
        service_runner: ServiceRunner[Any, Any],
    ) -> StrategyEvidenceBuilder:

        return StrategyEvidenceBuilder(
            events_service=events_service,
            service_runner=service_runner,
        )

    # Weighting Agent
    @provide
    def provide_weighting_agent(
        self,
    ) -> AdaptiveStrategyWeightingEngine:

        return AdaptiveStrategyWeightingEngine()
