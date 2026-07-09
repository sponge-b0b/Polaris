from dishka import Provider, Scope, provide

from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)

from intelligence.analysts.di import IntelligenceAnalystsDIProvider
from intelligence.attribution.di import IntelligenceAttributionDIProvider
from intelligence.execution.di import IntelligenceExecutionDIProvider
from intelligence.portfolio.di import IntelligencePortfolioDIProvider
from intelligence.research.di import IntelligenceResearchDIProvider
from intelligence.risk.di import IntelligenceRiskDIProvider
from intelligence.strategy.di import IntelligenceStrategyDIProvider


class IntelligenceDIProvider(Provider):
    scope = Scope.APP

    def __init__(self):
        super().__init__()

        self.from_context(
            IntelligenceAnalystsDIProvider(),
            scope=Scope.APP,
        )
        self.from_context(
            IntelligenceAttributionDIProvider(),
            scope=Scope.APP,
        )
        self.from_context(
            IntelligenceExecutionDIProvider(),
            scope=Scope.APP,
        )
        self.from_context(
            IntelligencePortfolioDIProvider(),
            scope=Scope.APP,
        )
        self.from_context(
            IntelligenceResearchDIProvider(),
            scope=Scope.APP,
        )
        self.from_context(
            IntelligenceRiskDIProvider(),
            scope=Scope.APP,
        )
        self.from_context(
            IntelligenceStrategyDIProvider(),
            scope=Scope.APP,
        )

    @provide
    def provide_intelligence_telemetry(
        self,
        observability_manager: ObservabilityManager,
    ) -> IntelligenceTelemetry:
        return IntelligenceTelemetry(
            observability_manager=observability_manager,
        )
