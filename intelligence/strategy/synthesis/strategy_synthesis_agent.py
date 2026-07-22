from __future__ import annotations

from collections.abc import Mapping
from time import perf_counter
from typing import Any

from application.observability import AiObservationStatus
from application.services.base import ServiceRequest, ServiceRunner
from application.services.market_events.market_events_request import MarketEventsRequest
from application.services.market_events.market_events_service import MarketEventsService
from config.strategy_model_config import StrategyModelConfig
from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from domain.authority import (
    authority_contract_metadata,
    model_authority_claims_from_payloads,
    strategy_synthesis_runtime_authority,
)
from domain.workflow_outputs import (
    STRATEGY_SYNTHESIS_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)
from intelligence.analysts.technical.technical_breadth_context import (
    extract_technical_breadth_context,
)
from intelligence.observability import (
    IntelligenceAiObservabilityProjectorPort,
    IntelligenceAiObservabilityRecorder,
    record_strategy_synthesis_observation,
)
from intelligence.strategy.hypothesis.contracts import StrategyPerspective
from intelligence.strategy.hypothesis.hypothesis import StrategyHypothesis
from intelligence.strategy.market_context import extract_symbol_constituents
from intelligence.strategy.model_usage import strategy_synthesis_usage
from intelligence.strategy.synthesis.contracts import (
    StrategyHypothesisEvaluation,
    StrategySynthesisDecision,
    StrategySynthesisDegradedReason,
    StrategySynthesisSelectionStatus,
)
from intelligence.strategy.synthesis.strategy_synthesis_policy import (
    StrategyMarketEvents,
    StrategySynthesisInputs,
    synthesize_strategy,
)
from intelligence.telemetry import telemetry_context_from_runtime

HIGH_HYPOTHESIS_DISAGREEMENT_THRESHOLD = 0.50


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
        strategy_model_config: StrategyModelConfig,
        ai_observability_projector: IntelligenceAiObservabilityProjectorPort
        | None = None,
    ) -> None:
        self.events_service = events_service
        self.service_runner = service_runner
        self.intelligence_telemetry = intelligence_telemetry
        self.ai_observability = IntelligenceAiObservabilityRecorder(
            ai_observability_projector
        )
        self.strategy_model_config = strategy_model_config

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        started_at = perf_counter()
        try:
            inputs = _strategy_synthesis_inputs_from_runtime(context)
        except MissingStrategySynthesisInput as exc:
            return await self._fallback_output(
                context=context,
                reason=exc.reason,
                latency_seconds=perf_counter() - started_at,
            )

        market_events = await self._get_market_events(
            inputs=inputs,
            context=context,
        )
        synthesis_output = synthesize_strategy(inputs, market_events)
        model_usage = strategy_synthesis_usage(
            model_config=self.strategy_model_config,
        )
        latency_seconds = perf_counter() - started_at

        await self._emit_synthesis_operational_telemetry(
            context=context,
            symbol=inputs.symbol,
            features=synthesis_output.features,
            confidence=synthesis_output.confidence,
            latency_seconds=latency_seconds,
        )

        if synthesis_output.confidence <= 0.40:
            await self._emit_low_confidence_telemetry(
                context=context,
                symbol=inputs.symbol,
                confidence=synthesis_output.confidence,
                uncertainty=synthesis_output.uncertainty,
            )

        await record_strategy_synthesis_observation(
            self.ai_observability,
            context=context,
            node_name=self.node_name,
            status=_strategy_observation_status_from_features(
                synthesis_output.features
            ),
            latency_seconds=latency_seconds,
            input_shape=(
                f"hypotheses=3;"
                f"constituents={len(inputs.symbol_constituents)};"
                f"event_horizon={inputs.event_lookahead_days}"
            ),
            output_shape=(
                f"evaluations={len(_mapping_sequence(synthesis_output.features.get('strategy_hypothesis_evaluations')))};"
                f"recommendations={len(synthesis_output.recommendations)}"
            ),
            metadata={
                **model_usage.to_metadata(),
                **_strategy_features_ai_metadata(
                    features=synthesis_output.features,
                    symbol=inputs.symbol,
                    recommendation_count=len(synthesis_output.recommendations),
                    confidence=synthesis_output.confidence,
                    uncertainty=synthesis_output.uncertainty,
                    fallback=False,
                ),
            },
        )

        return RuntimeNodeOutput.success_output(
            outputs=synthesis_output.to_runtime_outputs(),
            execution_metadata={
                **model_usage.to_metadata(),
                "node_name": self.node_name,
                "node_type": self.node_type,
                "confidence": synthesis_output.confidence,
                "source": "StrategySynthesisAgent",
                "risk_adjusted": True,
                "portfolio_constrained": True,
                "event_aware": True,
                "symbol": inputs.symbol,
                "quality_status": "normal",
                **authority_contract_metadata(
                    strategy_synthesis_runtime_authority(
                        model_authority_claims_from_payloads(
                            synthesis_output.to_runtime_outputs(),
                            synthesis_output.features,
                        )
                    )
                ),
            },
            output_contract=STRATEGY_SYNTHESIS_OUTPUT_CONTRACT,
            output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
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
        latency_seconds: float,
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
        model_usage = strategy_synthesis_usage(
            model_config=self.strategy_model_config,
        )
        await self._emit_fallback_operational_telemetry(
            context=context,
            decision=decision,
            reason=reason,
            latency_seconds=latency_seconds,
        )
        await record_strategy_synthesis_observation(
            self.ai_observability,
            context=context,
            node_name=self.node_name,
            status=AiObservationStatus.DEGRADED,
            latency_seconds=latency_seconds,
            input_shape="missing_required_inputs",
            output_shape=(
                f"evaluations={len(decision.evaluations)};"
                f"recommendations={len(decision.recommendations)}"
            ),
            metadata={
                **model_usage.to_metadata(),
                **_strategy_decision_ai_metadata(
                    decision=decision,
                    symbol=_string_value(
                        context.workflow_inputs.get("symbol"),
                        default="SPY",
                    ),
                    fallback=True,
                ),
                "fallback_reason": reason,
            },
        )
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
                    "hypothesis_synthesis_weights": {
                        evaluation.perspective.value: evaluation.synthesis_weight
                        for evaluation in decision.evaluations
                    },
                    "hypothesis_synthesis_disagreement": 1.0,
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
                **model_usage.to_metadata(),
                "node_name": self.node_name,
                "node_type": self.node_type,
                "confidence": decision.confidence,
                "fallback": True,
                "reason": reason,
                "quality_status": "fallback",
                **authority_contract_metadata(
                    strategy_synthesis_runtime_authority(
                        model_authority_claims_from_payloads(
                            decision.to_dict(),
                        )
                    )
                ),
            },
            output_contract=STRATEGY_SYNTHESIS_OUTPUT_CONTRACT,
            output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        )

    async def _emit_synthesis_operational_telemetry(
        self,
        *,
        context: RuntimeContext,
        symbol: str,
        features: Mapping[str, Any],
        confidence: float,
        latency_seconds: float,
    ) -> None:
        evaluations = _mapping_sequence(features.get("strategy_hypothesis_evaluations"))
        invalidated_perspectives = tuple(
            str(evaluation.get("perspective"))
            for evaluation in evaluations
            if evaluation.get("invalidated") is True
            and evaluation.get("perspective") is not None
        )
        if invalidated_perspectives:
            await self._emit_synthesis_signal(
                context=context,
                signal_name="strategy_synthesis.hypothesis_invalidated",
                telemetry_reason="hypothesis_invalidated",
                confidence=confidence,
                payload={
                    "symbol": symbol,
                    "invalidated_perspectives": list(invalidated_perspectives),
                    "invalidation_count": len(invalidated_perspectives),
                },
            )

        disagreement = _float_value(
            features.get("hypothesis_synthesis_disagreement"),
            default=0.0,
        )
        if disagreement >= HIGH_HYPOTHESIS_DISAGREEMENT_THRESHOLD:
            await self._emit_synthesis_signal(
                context=context,
                signal_name="strategy_synthesis.high_hypothesis_disagreement",
                telemetry_reason="high_hypothesis_disagreement",
                confidence=confidence,
                payload={
                    "symbol": symbol,
                    "hypothesis_synthesis_disagreement": disagreement,
                    "threshold": HIGH_HYPOTHESIS_DISAGREEMENT_THRESHOLD,
                    "synthesis_weights": dict(
                        _mapping(features.get("hypothesis_synthesis_weights"))
                    ),
                    "selected_perspective": _optional_string_value(
                        features.get("selected_perspective")
                    ),
                },
            )

        degraded_reasons = _string_sequence(features.get("degraded_reasons"))
        selected_perspective = _optional_string_value(
            features.get("selected_perspective")
        )
        selection_status = _string_value(
            features.get("selection_status"),
            default="unknown",
        )
        if selection_status == "degraded" and selected_perspective is None:
            await self._emit_synthesis_signal(
                context=context,
                signal_name="strategy_synthesis.degraded_neutral",
                telemetry_reason="degraded_neutral_synthesis",
                confidence=confidence,
                payload={
                    "symbol": symbol,
                    "fallback": False,
                    "selection_status": selection_status,
                    "selected_perspective": selected_perspective,
                    "degraded_reasons": list(degraded_reasons),
                },
            )

        await self._emit_synthesis_signal(
            context=context,
            signal_name="strategy_synthesis.completed",
            telemetry_reason="synthesis_completed",
            confidence=confidence,
            payload={
                "symbol": symbol,
                "latency_seconds": latency_seconds,
                "fallback": False,
                "selection_status": selection_status,
                "selected_perspective": selected_perspective,
                "degraded_reasons": list(degraded_reasons),
            },
        )

    async def _emit_fallback_operational_telemetry(
        self,
        *,
        context: RuntimeContext,
        decision: StrategySynthesisDecision,
        reason: str,
        latency_seconds: float,
    ) -> None:
        symbol = _string_value(context.workflow_inputs.get("symbol"), default="SPY")
        degraded_reasons = tuple(
            degraded_reason.value for degraded_reason in decision.degraded_reasons
        )
        if StrategySynthesisDegradedReason.MISSING_HYPOTHESIS in (
            decision.degraded_reasons
        ):
            await self._emit_synthesis_signal(
                context=context,
                signal_name="strategy_synthesis.missing_mandatory_hypothesis",
                telemetry_reason="missing_mandatory_hypothesis",
                confidence=0.0,
                payload={
                    "symbol": symbol,
                    "reason": reason,
                    "fallback": True,
                    "degraded_reasons": list(degraded_reasons),
                },
            )

        await self._emit_synthesis_signal(
            context=context,
            signal_name="strategy_synthesis.degraded_neutral",
            telemetry_reason="degraded_neutral_synthesis",
            confidence=decision.confidence,
            payload={
                "symbol": symbol,
                "reason": reason,
                "fallback": True,
                "selection_status": decision.selection_status.value,
                "selected_perspective": None,
                "degraded_reasons": list(degraded_reasons),
            },
        )
        await self._emit_synthesis_signal(
            context=context,
            signal_name="strategy_synthesis.completed",
            telemetry_reason="synthesis_completed",
            confidence=decision.confidence,
            payload={
                "symbol": symbol,
                "latency_seconds": latency_seconds,
                "reason": reason,
                "fallback": True,
                "selection_status": decision.selection_status.value,
                "selected_perspective": None,
                "degraded_reasons": list(degraded_reasons),
            },
        )

    async def _emit_synthesis_signal(
        self,
        *,
        context: RuntimeContext,
        signal_name: str,
        telemetry_reason: str,
        confidence: float,
        payload: dict[str, Any],
    ) -> None:
        await self.intelligence_telemetry.emit_agent_signal(
            agent_name=self.node_name,
            signal_name=signal_name,
            confidence=confidence,
            context=telemetry_context_from_runtime(
                context,
                node_name=self.node_name,
                attributes={"telemetry_reason": telemetry_reason},
            ),
            payload=payload,
        )


def _strategy_observation_status_from_features(
    features: Mapping[str, Any],
) -> AiObservationStatus:
    if (
        _string_value(features.get("selection_status"), default="unknown")
        == StrategySynthesisSelectionStatus.SELECTED.value
    ):
        return AiObservationStatus.SUCCESS
    return AiObservationStatus.DEGRADED


def _strategy_features_ai_metadata(
    *,
    features: Mapping[str, Any],
    symbol: str,
    recommendation_count: int,
    confidence: float,
    uncertainty: float,
    fallback: bool,
) -> dict[str, object]:
    evaluations = _mapping_sequence(features.get("strategy_hypothesis_evaluations"))
    invalidated_count = sum(
        1 for evaluation in evaluations if evaluation.get("invalidated") is True
    )
    degraded_reasons = _string_sequence(features.get("degraded_reasons"))
    return {
        "symbol": symbol,
        "selected_perspective": _optional_string_value(
            features.get("selected_perspective")
        ),
        "selection_status": _string_value(
            features.get("selection_status"),
            default="unknown",
        ),
        "evaluation_count": len(evaluations),
        "invalidated_count": invalidated_count,
        "degraded_reason_count": len(degraded_reasons),
        "recommendation_count": recommendation_count,
        "confidence": confidence,
        "uncertainty": uncertainty,
        "fallback": fallback,
    }


def _strategy_decision_ai_metadata(
    *,
    decision: StrategySynthesisDecision,
    symbol: str,
    fallback: bool,
) -> dict[str, object]:
    invalidated_count = sum(
        1 for evaluation in decision.evaluations if evaluation.invalidated
    )
    return {
        "symbol": symbol,
        "selected_perspective": (
            None
            if decision.selected_perspective is None
            else decision.selected_perspective.value
        ),
        "selection_status": decision.selection_status.value,
        "evaluation_count": len(decision.evaluations),
        "invalidated_count": invalidated_count,
        "degraded_reason_count": len(decision.degraded_reasons),
        "recommendation_count": len(decision.recommendations),
        "confidence": decision.confidence,
        "uncertainty": decision.uncertainty,
        "fallback": fallback,
    }


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


def _mapping_sequence(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _float_value(value: Any, *, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _string_value(value: Any, *, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _optional_string_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _string_sequence(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if item is not None)


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
            synthesis_weight=0.0,
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
