from dishka import Provider, Scope, provide

from intelligence.execution.execution_risk.execution_risk_guard import (
    ExecutionRiskGuard,
)
from intelligence.execution.trade_packaging.trade_packager import TradePackager


class IntelligenceExecutionDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # Execution Risk Guard
    @provide
    def provide_execution_risk_guard(
        self,
    ) -> ExecutionRiskGuard:

        return ExecutionRiskGuard()

    # Trade Packager
    @provide
    def provide_trade_packager(
        self,
    ) -> TradePackager:

        return TradePackager()
