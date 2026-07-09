from __future__ import annotations

from typing import Any

from application.services.base import ServiceRequest, ServiceRunner
from application.services.market_events.market_events_request import MarketEventsRequest
from application.services.market_events.market_events_service import MarketEventsService
from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from intelligence.strategy.synthesis.strategy_synthesis_policy import (
    MissingStrategySynthesisInput,
    StrategyMarketEvents,
    StrategySynthesisInputs,
    synthesize_strategy,
)
from intelligence.telemetry import telemetry_context_from_runtime


class StrategySynthesisAgent(RuntimeNode):
    """Orchestrates deterministic strategy synthesis and its service boundary."""

    node_name = "strategy_synthesis_agent"
    node_type = "strategy_synthesis"

    def __init__(
        self,
        events_service: MarketEventsService,
        service_runner: ServiceRunner[Any, Any],
        intelligence_telemetry: IntelligenceTelemetry,
    ) -> None:
        self.events_service = events_service
        self.service_runner = service_runner
        self.intelligence_telemetry = intelligence_telemetry

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        try:
            inputs = StrategySynthesisInputs.from_runtime_payloads(
                workflow_inputs=context.workflow_inputs,
                node_outputs=context.node_outputs,
            )
        except MissingStrategySynthesisInput as exc:
            return await self._fallback_output(context=context, reason=exc.reason)

        market_events = await self._get_market_events(
            inputs=inputs,
            context=context,
        )
        decision = synthesize_strategy(inputs, market_events)

        if decision.confidence <= 0.40:
            await self._emit_low_confidence_telemetry(
                context=context,
                symbol=inputs.symbol,
                confidence=decision.confidence,
                uncertainty=decision.uncertainty,
            )

        return RuntimeNodeOutput.success_output(
            outputs=decision.to_runtime_outputs(),
            execution_metadata={
                "node_name": self.node_name,
                "node_type": self.node_type,
                "confidence": decision.confidence,
                "source": "StrategySynthesisAgent",
                "risk_adjusted": True,
                "portfolio_constrained": True,
                "event_aware": True,
                "symbol": inputs.symbol,
            },
        )

    async def _get_market_events(
        self,
        *,
        inputs: StrategySynthesisInputs,
        context: RuntimeContext,
    ) -> StrategyMarketEvents:
        try:
            service_result = await self.service_runner.run(
                service=self.events_service,
                request=ServiceRequest(
                    payload=MarketEventsRequest(
                        symbol=inputs.symbol,
                        lookahead_days=inputs.event_lookahead_days,
                        horizon=inputs.horizon,
                        symbol_constituents=inputs.symbol_constituents,
                    ),
                    telemetry_context=telemetry_context_from_runtime(
                        context,
                        node_name=self.node_name,
                    ),
                ),
            )
            service_result.raise_if_failed()

            if service_result.result is None:
                error = "Market events service returned no data"
                await self._emit_degraded_data_quality_telemetry(
                    context=context,
                    symbol=inputs.symbol,
                    reason=error,
                )
                return StrategyMarketEvents.neutral(
                    symbol=inputs.symbol,
                    error=error,
                )

            return StrategyMarketEvents.from_service_result(service_result.result)
        except Exception as exc:
            error = str(exc) or exc.__class__.__name__
            await self._emit_degraded_data_quality_telemetry(
                context=context,
                symbol=inputs.symbol,
                reason=error,
            )
            return StrategyMarketEvents.neutral(
                symbol=inputs.symbol,
                error=error,
            )

    async def _emit_low_confidence_telemetry(
        self,
        *,
        context: RuntimeContext,
        symbol: str,
        confidence: float,
        uncertainty: float,
    ) -> None:
        await self.intelligence_telemetry.emit_agent_signal(
            agent_name=self.node_name,
            signal_name="strategy_synthesis.low_confidence",
            confidence=confidence,
            context=telemetry_context_from_runtime(
                context,
                node_name=self.node_name,
                attributes={"telemetry_reason": "low_confidence"},
            ),
            payload={
                "symbol": symbol,
                "confidence": confidence,
                "uncertainty": uncertainty,
            },
        )

    async def _emit_degraded_data_quality_telemetry(
        self,
        *,
        context: RuntimeContext,
        symbol: str,
        reason: str,
    ) -> None:
        await self.intelligence_telemetry.emit_agent_signal(
            agent_name=self.node_name,
            signal_name="strategy_synthesis.degraded_data_quality",
            confidence=0.0,
            context=telemetry_context_from_runtime(
                context,
                node_name=self.node_name,
                attributes={"telemetry_reason": "degraded_data_quality"},
            ),
            payload={"symbol": symbol, "reason": reason},
        )

    async def _fallback_output(
        self,
        *,
        context: RuntimeContext,
        reason: str,
    ) -> RuntimeNodeOutput:
        await self.intelligence_telemetry.emit_agent_signal(
            agent_name=self.node_name,
            signal_name="strategy_synthesis.fallback_output",
            confidence=0.25,
            context=telemetry_context_from_runtime(
                context,
                node_name=self.node_name,
                attributes={"telemetry_reason": "fallback_output"},
            ),
            payload={"reason": reason, "fallback": True},
        )
        return RuntimeNodeOutput.success_output(
            outputs={
                "directional_score": 0.0,
                "confidence": 0.25,
                "regime": "neutral",
                "signals": ["fallback_mode"],
                "risks": ["strategy_synthesis_failure"],
                "recommendations": [
                    "reduce_exposure",
                    "validate_upstream_nodes",
                ],
                "features": {"fallback_reason": reason},
            },
            execution_metadata={
                "node_name": self.node_name,
                "node_type": self.node_type,
                "confidence": 0.25,
                "fallback": True,
                "reason": reason,
            },
        )
