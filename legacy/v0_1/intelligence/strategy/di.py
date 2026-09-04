from typing import Any

from dishka import Provider, Scope, provide

from application.services.base import ServiceRunner
from application.services.market_events.market_events_service import (
    MarketEventsService,
)
from config.settings import Settings
from config.strategy_model_config import StrategyModelConfig
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from intelligence.strategy.bear.bear_agent import BearAgent
from intelligence.strategy.bull.bull_agent import BullAgent
from intelligence.strategy.hypothesis.evidence_builder import (
    StrategyEvidenceBuilder,
)
from intelligence.strategy.sideways.sideways_agent import SidewaysAgent
from intelligence.strategy.synthesis.strategy_synthesis_agent import (
    StrategySynthesisAgent,
)
from intelligence.strategy.weighting.strategy_perspective_weighting_engine import (
    StrategyPerspectiveWeightingEngine,
)


class IntelligenceStrategyDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    @provide
    def provide_strategy_model_config(
        self,
        settings: Settings,
    ) -> StrategyModelConfig:

        return StrategyModelConfig.from_settings(settings)

    # Bear Agent
    @provide
    def provide_bear_agent(
        self,
        strategy_model_config: StrategyModelConfig,
    ) -> BearAgent:

        return BearAgent(strategy_model_config=strategy_model_config)

    # Bull Agent
    @provide
    def provide_bull_agent(
        self,
        strategy_model_config: StrategyModelConfig,
    ) -> BullAgent:

        return BullAgent(strategy_model_config=strategy_model_config)

    # Sideways Agent
    @provide
    def provide_sideways_agent(
        self,
        strategy_model_config: StrategyModelConfig,
    ) -> SidewaysAgent:

        return SidewaysAgent(strategy_model_config=strategy_model_config)

    # Synthesis Agent
    @provide
    def provide_synthesis_agent(
        self,
        events_service: MarketEventsService,
        service_runner: ServiceRunner[Any, Any],
        intelligence_telemetry: IntelligenceTelemetry,
        strategy_model_config: StrategyModelConfig,
    ) -> StrategySynthesisAgent:

        return StrategySynthesisAgent(
            events_service=events_service,
            service_runner=service_runner,
            intelligence_telemetry=intelligence_telemetry,
            strategy_model_config=strategy_model_config,
        )

    # Strategy Evidence Builder
    @provide
    def provide_strategy_evidence_builder(
        self,
        events_service: MarketEventsService,
        service_runner: ServiceRunner[Any, Any],
        intelligence_telemetry: IntelligenceTelemetry,
    ) -> StrategyEvidenceBuilder:

        return StrategyEvidenceBuilder(
            events_service=events_service,
            service_runner=service_runner,
            intelligence_telemetry=intelligence_telemetry,
        )

    # Strategy Perspective Weighting Agent
    @provide
    def provide_perspective_weighting_agent(
        self,
    ) -> StrategyPerspectiveWeightingEngine:

        return StrategyPerspectiveWeightingEngine()
