from __future__ import annotations

from typing import Any

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput

from application.services.portfolio.portfolio_service import PortfolioService
from application.services.base import ServiceRequest
from application.services.base import ServiceRunner
from application.services.portfolio.portfolio_request import (
    PortfolioAnalysisRequest,
)
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from domain.workflow_outputs import (
    PORTFOLIO_STATE_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)
from intelligence.telemetry import telemetry_context_from_runtime
from intelligence.portfolio.management.portfolio_state_policy import (
    build_portfolio_state_decision,
)


class PortfolioStateBuilder(RuntimeNode):
    """
    Polaris Portfolio State Builder

    ============================================================
    PURPOSE
    ============================================================
    Canonical portfolio normalization + analytics node.

    SINGLE SOURCE OF TRUTH FOR:
        - portfolio state
        - equity state
        - normalized positions
        - exposure metrics
        - risk features

    ============================================================
    ARCHITECTURE
    ============================================================
    PROVIDER LAYER:
        Handles ALL external data access.

    SERVICES:
        Pure deterministic compute only.

    THIS NODE:
        Orchestrates provider -> services -> normalized state.

    ============================================================
    IMPORTANT
    ============================================================
    Polaris DOES NOT execute trades.

    Polaris ONLY:
        - consumes broker portfolio state
        - consumes market data
        - generates intelligence

    This node is fully compatible with:
        - live trading intelligence
        - historical simulation
        - backtesting
        - replay systems
    """

    node_name = "portfolio_state_builder"
    node_type = "portfolio_intelligence"

    # ============================================================
    # INIT
    # ============================================================

    def __init__(
        self,
        portfolio_service: PortfolioService,
        service_runner: ServiceRunner[Any, Any],
        intelligence_telemetry: IntelligenceTelemetry,
    ) -> None:

        # ========================================================
        # PROVIDER LAYER
        # ========================================================

        self.portfolio_service = portfolio_service
        self.service_runner = service_runner
        self.intelligence_telemetry = intelligence_telemetry

    # ============================================================
    # EXECUTE
    # ============================================================

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        symbol = str(context.workflow_inputs.get("symbol", "SPY")).upper()
        portfolio_result = await self.service_runner.run(
            service=self.portfolio_service,
            request=ServiceRequest(
                payload=PortfolioAnalysisRequest(symbol=symbol),
                telemetry_context=telemetry_context_from_runtime(
                    context,
                    node_name=self.node_name,
                ),
            ),
        )
        portfolio_result.raise_if_failed()

        if portfolio_result.result is None:
            raise RuntimeError("Portfolio service returned no result data.")

        decision = build_portfolio_state_decision(portfolio_result.result)

        await self.intelligence_telemetry.emit_agent_signal(
            agent_name=self.node_name,
            signal_name="portfolio.state_built",
            confidence=1.0,
            context=telemetry_context_from_runtime(
                context,
                node_name=self.node_name,
            ),
            payload={
                "symbol": symbol,
                "position_count": decision.position_count,
                "drawdown_percent": decision.drawdown_percent,
            },
        )

        return RuntimeNodeOutput.success_output(
            outputs=decision.to_runtime_outputs(),
            execution_metadata={
                "node_name": self.node_name,
                "node_type": self.node_type,
                "confidence": 1.0,
                "symbol": symbol,
                "position_count": decision.position_count,
                "quality_status": "normal",
            },
            output_contract=PORTFOLIO_STATE_OUTPUT_CONTRACT,
            output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        )
