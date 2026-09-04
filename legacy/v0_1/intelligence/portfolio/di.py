from dishka import Provider, Scope, provide

from application.services.base import ServiceRunner
from application.services.portfolio.portfolio_service import PortfolioService
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from intelligence.portfolio.management.portfolio_manager_agent import (
    PortfolioManagerAgent,
)
from intelligence.portfolio.management.portfolio_state_builder import (
    PortfolioStateBuilder,
)


class IntelligencePortfolioDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # Portfolio Manager Agent
    @provide
    def provide_portfolio_manager_agent(
        self,
    ) -> PortfolioManagerAgent:

        return PortfolioManagerAgent()

    # Portfolio State Builder
    @provide(scope=Scope.REQUEST)
    def provide_portfolio_state_builder(
        self,
        portfolio_service: PortfolioService,
        service_runner: ServiceRunner,
        intelligence_telemetry: IntelligenceTelemetry,
    ) -> PortfolioStateBuilder:

        return PortfolioStateBuilder(
            portfolio_service=portfolio_service,
            service_runner=service_runner,
            intelligence_telemetry=intelligence_telemetry,
        )
