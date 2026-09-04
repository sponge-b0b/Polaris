from dishka import Provider, Scope, provide

from intelligence.risk.aggregation.risk_aggregator_agent import RiskAggregatorAgent
from intelligence.risk.aggregation.risk_signal_builder import RiskSignalBuilder
from intelligence.risk.drawdown.drawdown_risk_agent import DrawdownRiskAgent
from intelligence.risk.exposure.exposure_risk_agent import ExposureRiskAgent
from intelligence.risk.volatility.volatility_risk_agent import VolatilityRiskAgent


class IntelligenceRiskDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # Risk Aggregator Agent
    @provide
    def provide_risk_aggregator_agent(
        self,
    ) -> RiskAggregatorAgent:

        return RiskAggregatorAgent()

    # Risk Signal Builder
    @provide
    def provide_signal_builder(
        self,
    ) -> RiskSignalBuilder:

        return RiskSignalBuilder()

    # Drawdown Risk Agent
    @provide
    def provide_drawdown_risk_agent(
        self,
    ) -> DrawdownRiskAgent:

        return DrawdownRiskAgent()

    # Exposure Risk Agent
    @provide
    def provide_exposure_risk_agent(
        self,
    ) -> ExposureRiskAgent:

        return ExposureRiskAgent()

    # Volatility Risk Agent
    @provide
    def provide_volatility_risk_agent(
        self,
    ) -> VolatilityRiskAgent:

        return VolatilityRiskAgent()
