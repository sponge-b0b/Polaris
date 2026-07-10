from __future__ import annotations

from typing import Any
from typing import Mapping

from application.services.base import ServiceRequest, ServiceRunner
from application.services.market_events.market_events_request import MarketEventsRequest
from application.services.market_events.market_events_service import MarketEventsService
from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from intelligence.analysts.technical.technical_breadth_context import (
    extract_technical_breadth_context,
)
from intelligence.strategy.hypothesis.contracts import StrategyPerspective
from intelligence.strategy.hypothesis.hypothesis import StrategyHypothesis
from intelligence.strategy.synthesis.contracts import StrategyHypothesisEvaluation
from intelligence.strategy.synthesis.contracts import StrategySynthesisDecision
from intelligence.strategy.synthesis.contracts import StrategySynthesisDegradedReason
from intelligence.strategy.synthesis.contracts import StrategySynthesisSelectionStatus
from intelligence.strategy.market_context import extract_symbol_constituents
from intelligence.strategy.synthesis.strategy_synthesis_policy import (
    StrategyMarketEvents,
    StrategySynthesisInputs,
    synthesize_strategy,
)
from intelligence.telemetry import telemetry_context_from_runtime


class MissingStrategySynthesisInput(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


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
            inputs = _strategy_synthesis_inputs_from_runtime(context)
        except MissingStrategySynthesisInput as exc:
            return await self._fallback_output(context=context, reason=exc.reason)

        market_events = await self._get_market_events(
            inputs=inputs,
            context=context,
        )
        synthesis_output = synthesize_strategy(inputs, market_events)

        if synthesis_output.confidence <= 0.40:
            await self._emit_low_confidence_telemetry(
                context=context,
                symbol=inputs.symbol,
                confidence=synthesis_output.confidence,
                uncertainty=synthesis_output.uncertainty,
            )

        return RuntimeNodeOutput.success_output(
            outputs=synthesis_output.to_runtime_outputs(),
            execution_metadata={
                "node_name": self.node_name,
                "node_type": self.node_type,
                "confidence": synthesis_output.confidence,
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
        decision = _degraded_neutral_decision(reason)
        return RuntimeNodeOutput.success_output(
            outputs={
                "directional_score": decision.directional_score,
                "confidence": decision.confidence,
                "regime": decision.regime,
                "signals": list(decision.signals),
                "risks": list(decision.risks),
                "recommendations": list(decision.recommendations),
                "features": {
                    "fallback_reason": reason,
                    "strategy_synthesis_decision": decision.to_dict(),
                    "strategy_hypothesis_evaluations": [
                        evaluation.to_dict() for evaluation in decision.evaluations
                    ],
                    "hypothesis_candidate_scores": {
                        evaluation.perspective.value: evaluation.candidate_score
                        for evaluation in decision.evaluations
                    },
                    "hypothesis_posterior_weights": {
                        evaluation.perspective.value: evaluation.posterior_weight
                        for evaluation in decision.evaluations
                    },
                    "hypothesis_posterior_disagreement": 1.0,
                    "selected_hypothesis": None,
                    "selected_perspective": None,
                    "selection_status": decision.selection_status.value,
                    "degraded_reasons": [
                        degraded_reason.value
                        for degraded_reason in decision.degraded_reasons
                    ],
                    "thesis": decision.thesis,
                },
            },
            execution_metadata={
                "node_name": self.node_name,
                "node_type": self.node_type,
                "confidence": decision.confidence,
                "fallback": True,
                "reason": reason,
            },
        )


def _strategy_synthesis_inputs_from_runtime(
    context: RuntimeContext,
) -> StrategySynthesisInputs:
    node_outputs = context.node_outputs
    weighting_output = _required_output(
        node_outputs,
        "strategy_perspective_weighting_engine",
    )
    risk_output = _required_output(node_outputs, "risk_aggregator_agent")
    portfolio_output = _required_output(node_outputs, "portfolio_state_builder")
    technical_output = _required_output(node_outputs, "technical_agent")
    bull_hypothesis = _required_strategy_hypothesis(
        node_outputs,
        "bull_agent",
        StrategyPerspective.BULL,
    )
    bear_hypothesis = _required_strategy_hypothesis(
        node_outputs,
        "bear_agent",
        StrategyPerspective.BEAR,
    )
    sideways_hypothesis = _required_strategy_hypothesis(
        node_outputs,
        "sideways_agent",
        StrategyPerspective.SIDEWAYS,
    )

    weighting_features = _features(weighting_output)
    risk_features = _features(risk_output)
    portfolio_features = _features(portfolio_output)
    technical_features = _features(technical_output)
    technical_regime = _mapping(technical_features.get("regime"))

    risk_pressure = float(risk_features.get("risk_pressure", 0.0))
    return StrategySynthesisInputs(
        symbol=str(context.workflow_inputs.get("symbol", "SPY")),
        event_lookahead_days=int(
            context.workflow_inputs.get("event_lookahead_days", 10)
        ),
        horizon=str(context.workflow_inputs.get("horizon", "3month")),
        bull_weight=float(weighting_features.get("bull_weight", 0.33)),
        bear_weight=float(weighting_features.get("bear_weight", 0.33)),
        sideways_weight=float(weighting_features.get("sideways_weight", 0.34)),
        bull_hypothesis=bull_hypothesis,
        bear_hypothesis=bear_hypothesis,
        sideways_hypothesis=sideways_hypothesis,
        adjusted_risk_pressure=float(
            risk_features.get("adjusted_risk_pressure", risk_pressure)
        ),
        composite_risk=float(risk_features.get("composite_risk", 0.0)),
        portfolio_scale_factor=float(portfolio_features.get("scale_factor", 1.0)),
        portfolio_status=str(portfolio_features.get("status", "unknown")),
        technical_regime=str(technical_regime.get("regime", "neutral")),
        breadth_context=extract_technical_breadth_context(technical_output),
        symbol_constituents=extract_symbol_constituents(
            technical_features.get("market_context")
        ),
    )


def _required_output(
    node_outputs: Mapping[str, Any],
    node_name: str,
) -> Mapping[str, Any]:
    output = node_outputs.get(node_name)
    if not isinstance(output, Mapping) or output.get("outputs", {}) is None:
        raise MissingStrategySynthesisInput(f"missing_{node_name}")
    return output


def _required_strategy_hypothesis(
    node_outputs: Mapping[str, Any],
    node_name: str,
    expected_perspective: StrategyPerspective,
) -> StrategyHypothesis:
    output = _required_output(node_outputs, node_name)
    strategy_hypothesis = _mapping(output.get("outputs")).get("strategy_hypothesis")
    if not isinstance(strategy_hypothesis, Mapping):
        raise MissingStrategySynthesisInput(f"missing_{node_name}_strategy_hypothesis")
    try:
        hypothesis = StrategyHypothesis.from_dict(
            {str(key): value for key, value in strategy_hypothesis.items()}
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise MissingStrategySynthesisInput(
            f"invalid_{node_name}_strategy_hypothesis"
        ) from exc
    if hypothesis.perspective is not expected_perspective:
        raise MissingStrategySynthesisInput(
            f"invalid_{node_name}_strategy_hypothesis_perspective"
        )
    return hypothesis


def _features(output: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(_mapping(output.get("outputs")).get("features"))


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _degraded_neutral_decision(reason: str) -> StrategySynthesisDecision:
    degraded_reasons = _fallback_degraded_reasons(reason)
    evaluations = tuple(
        StrategyHypothesisEvaluation(
            perspective=perspective,
            perspective_weight=0.0,
            contradiction_burden=0.0,
            assumption_support=0.0,
            invalidated=True,
            candidate_score=0.0,
            posterior_weight=0.0,
            rank=index,
            selection_status=StrategySynthesisSelectionStatus.INVALIDATED,
            degraded_reasons=degraded_reasons,
        )
        for index, perspective in enumerate(
            (
                StrategyPerspective.BULL,
                StrategyPerspective.BEAR,
                StrategyPerspective.SIDEWAYS,
            ),
            start=1,
        )
    )
    thesis = f"Strategy synthesis is degraded because {reason}."
    return StrategySynthesisDecision.from_evaluations(
        evaluations=evaluations,
        directional_score=0.0,
        confidence=0.25,
        regime="neutral",
        uncertainty=1.0,
        thesis=thesis,
        signals=("fallback_mode",),
        risks=("strategy_synthesis_failure",),
        recommendations=("reduce_exposure", "validate_upstream_nodes"),
        degraded_reasons=degraded_reasons,
    )


def _fallback_degraded_reasons(
    reason: str,
) -> tuple[StrategySynthesisDegradedReason, ...]:
    reasons = [StrategySynthesisDegradedReason.SYNTHESIS_INPUT_UNAVAILABLE]
    if "hypothesis" in reason or reason in {
        "missing_bull_agent",
        "missing_bear_agent",
        "missing_sideways_agent",
    }:
        reasons.append(StrategySynthesisDegradedReason.MISSING_HYPOTHESIS)
    if "strategy_perspective_weighting_engine" in reason:
        reasons.append(StrategySynthesisDegradedReason.MISSING_PERSPECTIVE_WEIGHT)
    return tuple(dict.fromkeys(reasons))
